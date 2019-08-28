import time

import numpy as np
import tcn
from keras import models
from keras.layers import Dense, Activation


def preproccess(keypoints, actions):
    # 动作的结束点减起始点，从而获取每一个动作的长度
    lenght = actions[..., 1] - actions[..., 0]
    # 过滤掉太长的和太短的，甚至长度为负数的动作…
    actions = actions[np.logical_and(4 < lenght, lenght < 64)]
    # 将其翻译成方便机器学习的数据结构
    n = keypoints.shape[0]
    y = np.zeros(n, dtype='int32')
    w = np.zeros(n, dtype='float32')
    for i, (start, last, action) in enumerate(actions):
        for j in range(start, last + 1):
            y[j] = action
            w[j] = (j - start + 1) / (last - start + 1)

    # 开始进行真正的预处理
    epsilon = 1e-7
    # 忽略置信度
    x = keypoints[..., :2].copy()
    x -= x.mean(1, keepdims=True)
    x /= x.max(1, keepdims=True) - x.min(1, keepdims=True) + epsilon

    return x, y, w


def build_model(x, y):
    i = models.Input(batch_shape=(None, None, x.shape[2]))
    o = tcn.TCN(dropout_rate=0.15, dilations=[4, 8, 16, 32], return_sequences=True)(i)
    o = Dense(y.max() + 1)(o)
    o = Activation('softmax')(o)
    m = models.Model(i, o)
    return m


def _load_data(data):
    x, y, w = preproccess(data['keypoints'], data['actions'])
    print('data.shape:', x.shape, y.shape, w.shape)
    n = int(x.shape[0] * 0.9)
    x_test = x[n:]
    y_test = y[n:]
    w_test = w[n:]
    x = x[:n]
    y = y[:n]
    w = w[:n]
    x.shape = 1, -1, 12
    y.shape = 1, -1, 1
    w.shape = 1, -1
    x_test.shape = 1, -1, 12
    y_test.shape = 1, -1, 1
    w_test.shape = 1, -1
    return (x, y, w), (x_test, y_test, w_test)


'''
# m = build_model(x, y)
m = models.load_model('first.h5')
y_test_pred = m.predict(x_test)
y_test_pred.shape = -1, y.max() + 1
y_test_pred_p = y_test_pred.max(1)
y_test_pred = y_test_pred.argmax(1)
y_test.shape = -1
w_test.shape = -1
'''

'''
x_test.shape = -1, 6, 2
for y_true, y_pred, w, p, x in zip(y_test, y_test_pred, w_test, y_test_pred_p, x_test):
    if w >= 0:
        print(l[y_true], l[y_pred], w, p)
        print(x)
exit()
'''

if __name__ == '__main__':
    data = np.load('actions.npz')
    (x, y, w), (x_test, y_test, w_test) = _load_data(data)
    m = build_model(x, y)
    m.compile(optimizer='rmsprop',
              loss='sparse_categorical_crossentropy',
              sample_weight_mode='temporal')
    m.fit(x, y, sample_weight=w, epochs=1600,
          validation_data=(x_test, y_test, w_test))
    m.save(f'model.{int(time.time())}.h5', include_optimizer=False)
