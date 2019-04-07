from model import Model
from load_data import Datagen, plot_data
import tensorflow as tf
from util import plot_segm_map, calc_iou
import numpy as np
import networkx as nx
import adjacency
import matplotlib.pyplot as plt
import math

G = nx.Graph()
nodes = np.array(list(range(32 * 32)))
G.add_nodes_from(nodes)
# グリッド状グラフの全辺リストを生成
edges = []
grid = adjacency.grid_points([32, 32])
for _grid in grid:
    edges.append((_grid[0], _grid[1]))
    edges.append((_grid[1], _grid[0]))
# グラフにグリッド辺を追加
G.add_edges_from(edges)

"""
# グラフ表示
pos = nx.spring_layout(G)
nx.draw_networkx(G, pos, with_labels=True)
plt.axis("off")
plt.show()
"""

# グラフコンボリューションのための行列を用意
A = nx.adjacency_matrix(G).astype("float32")
D = nx.laplacian_matrix(G).astype("float32") + A
for i in range(G.number_of_nodes()):
    D[i, i] = 1 / math.sqrt(D[i, i])
A_chil_ = D.dot(A.dot(D))


# scipy.sparse -> tf.SparseTensorへの変換のための関数
def convert_sparse_matrix_to_sparse_tensor(X):
    coo = X.tocoo()
    indices = np.mat([coo.row, coo.col]).transpose()
    return tf.SparseTensor(indices, coo.data, coo.shape)


# GCN layerを出力する関数
def GCN_layer(A, layer_input, W, activation):
    if activation is None:
        return tf.matmul(tf.sparse.matmul(A, layer_input), W)
    else:
        return activation(tf.matmul(tf.sparse.matmul(A, layer_input), W))


d = 1  # 最終出力の次元
hidden_size = 8  # 1層目の出力サイズ
learning_rate = 1e-3  # 学習率

# モデル定義
X = tf.placeholder(tf.float32, shape=[G.number_of_nodes(), 2 ** 8])
A_chil = convert_sparse_matrix_to_sparse_tensor(A_chil_)
W_1 = tf.Variable(tf.random_normal([2 ** 8, hidden_size]), dtype=tf.float32)
W_2 = tf.Variable(tf.random_normal([hidden_size, d]), dtype=tf.float32)

L1 = GCN_layer(A_chil, X, W_1, tf.nn.relu)
L2 = GCN_layer(A_chil, L1, W_2, None)

A_rec = tf.sigmoid(tf.matmul(L2, tf.transpose(L2)))

loss = tf.nn.l2_loss(tf.sparse.add(-1 * A_rec, A_chil))
train = tf.train.AdamOptimizer(learning_rate).minimize(loss)

batch_size = 1
dg = Datagen('data/mnist', 'data/cifar')
data, segm_map = dg.sample(batch_size, norm=False)

# 学習部分
epoch = 1000
# x = np.identity(G.number_of_nodes(), dtype="float32")
with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())
    loss_list = list()
    for e in range(epoch):
        # 学習
        data_batch, segm_map_batch = dg.sample(batch_size, norm=False)
        data_batch = data_batch.reshape([3, 1024])[0]
        print("#{} pre_databatch:{}".format(e, data_batch))
        data_batch = np.array(data_batch, dtype=np.int64)
        data_batch = np.identity(256)[data_batch]
        print("#{} databatch:{}".format(e, data_batch))
        x = data_batch.reshape([G.number_of_nodes(), 256])
        tloss, _ = sess.run([loss, train], feed_dict={X: x})
        loss_list.append(tloss)

        """
        # 学習結果の出力
        if (e + 1) % 100 == 0:
            emb = sess.run(L2, feed_dict={X: x})
            fig, ax = plt.subplots()
            for i in range(G.number_of_nodes()):
                ax.scatter(emb[i][0], emb[i][1], color=color[i])
            plt.title("epoch" + str(e + 1))
            plt.show()
            plt.title("epoch" + str(e + 1))
            nx.draw_networkx(G, pos=emb, node_color=color)
            plt.show()
        """

"""
batch_size = 64
dropout = 0.7

dg = Datagen('data/mnist', 'data/cifar')
data, segm_map = dg.sample(batch_size)
model = Model(batch_size, dropout)

num_iter = 500

sess = tf.Session()

sess.run(tf.global_variables_initializer())
for iter in range(num_iter):
    data_batch, segm_map_batch = dg.sample(batch_size)
    train_loss, _ = sess.run([model.total_loss, model.train_step],
                             feed_dict={model.image: data_batch, model.segm_map: segm_map_batch})

    if iter % 50 == 0:
        data_batch, segm_map_batch = dg.sample(batch_size, dataset='test')
        test_loss, segm_map_pred = sess.run([model.total_loss, model.h4],
                                            feed_dict={model.image: data_batch, model.segm_map: segm_map_batch})
        print('iter %5i/%5i loss is %5.3f and mIOU %5.3f' % (
            iter, num_iter, test_loss, calc_iou(segm_map_batch, segm_map_pred)))

# Final run
data_batch, segm_map_batch = dg.sample(batch_size, dataset='test')
test_loss, segm_map_pred = sess.run([model.total_loss, model.h4],
                                    feed_dict={model.image: data_batch, model.segm_map: segm_map_batch})
plot_segm_map(data_batch, segm_map_batch, segm_map_pred)
"""
