"""
    Inception Score
    Created by Jet-Tsyn Lee 01/08/2018
    Last Update v0.5 31/08/2018

    Evaluates images against the ImageNet inception score
"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import os
import os.path
import sys
import tarfile

import numpy as np
from six.moves import urllib
import tensorflow as tf
from glob import glob
import scipy.misc
import math
import sys
import time


class Inception:

    def __init__(self, test_dir):
          self.test_dir = test_dir


MODEL_DIR = '/tmp/imagenet'
DATA_URL = 'http://download.tensorflow.org/models/image/imagenet/inception-2015-12-05.tgz'
softmax = None



# Call this function with list of images. Each of elements should be a 
# numpy array with values ranging from 0 to 255.
def get_inception_score(images, splits=10):

    assert(type(images) == list)
    assert(type(images[0]) == np.ndarray)
    assert(len(images[0].shape) == 3)
    assert(np.max(images[0]) > 10)
    assert(np.min(images[0]) >= 0.0)
    inps = []


    for img in images:
        img = img.astype(np.float32)
        inps.append(np.expand_dims(img, 0))

    bs = 1

    with tf.Session(config=tf.ConfigProto(log_device_placement=False, gpu_options=tf.GPUOptions(allow_growth=True))) as sess:

        preds = []
        n_batches = int(math.ceil(float(len(inps)) / float(bs)))

        for i in range(n_batches):

            inp = inps[(i * bs):min((i + 1) * bs, len(inps))]
            inp = np.concatenate(inp, 0)
            pred = sess.run(softmax, {'ExpandDims:0': inp})
            preds.append(pred)


        preds = np.concatenate(preds, 0)
        scores = []


        for i in range(splits):
            part = preds[(i * preds.shape[0] // splits):((i + 1) * preds.shape[0] // splits), :]
            kl = part * (np.log(part) - np.log(np.expand_dims(np.mean(part, 0), 0)))
            kl = np.mean(np.sum(kl, 1))
            scores.append(np.exp(kl))

        return np.mean(scores), np.std(scores)





# This function is called automatically.
def _init_inception():
    global softmax

    if not os.path.exists(MODEL_DIR):
        os.makedirs(MODEL_DIR)

    filename = DATA_URL.split('/')[-1]
    filepath = os.path.join(MODEL_DIR, filename)

    if not os.path.exists(filepath):

        def _progress(count, block_size, total_size):
            sys.stdout.write('\r>> Downloading %s %.1f%%' % (filename, float(count * block_size) / float(total_size) * 100.0))
            sys.stdout.flush()

        filepath, _ = urllib.request.urlretrieve(DATA_URL, filepath, _progress)
        print()
        statinfo = os.stat(filepath)
        print('Succesfully downloaded', filename, statinfo.st_size, 'bytes.')


    tarfile.open(filepath, 'r:gz').extractall(MODEL_DIR)
    with tf.gfile.FastGFile(os.path.join(MODEL_DIR, 'classify_image_graph_def.pb'), 'rb') as f:
        graph_def = tf.GraphDef()
        graph_def.ParseFromString(f.read())
        _ = tf.import_graph_def(graph_def, name='')


    # Works with an arbitrary minibatch size.
    with tf.Session(config=tf.ConfigProto(log_device_placement=False, gpu_options=tf.GPUOptions(allow_growth=True))) as sess:
        pool3 = sess.graph.get_tensor_by_name('pool_3:0')
        ops = pool3.graph.get_operations()

        for op_idx, op in enumerate(ops):
            for o in op.outputs:
                shape = o.get_shape()
                shape = [s.value for s in shape]
                new_shape = []
                for j, s in enumerate(shape):
                    if s == 1 and j == 0:
                        new_shape.append(None)
                    else:
                        new_shape.append(s)
                o.set_shape(tf.TensorShape(new_shape))

        w = sess.graph.get_operation_by_name("softmax/logits/MatMul").inputs[1]
        logits = tf.matmul(tf.squeeze(pool3, [1, 2]), w)
        softmax = tf.nn.softmax(logits)




# Load image
def get_images(filename):
    return scipy.misc.imread(filename)


if __name__ == "__main__":

    log_date = time.strftime("%d%b%Y%H%M%S", time.localtime(time.time()))

    if softmax is None:
        _init_inception()

    # Read image
    data_path = "./Files"
    log_dir = "./Results"
    res_dir = os.path.join(log_dir,log_date)

    test_dir = os.listdir(data_path)
    print(test_dir)


    if not os.path.exists(res_dir):
        os.makedirs(res_dir)

    inv_path = os.path.join(res_dir, log_date+"_individual_results.txt")

    for folder in test_dir:

        file_dir = os.path.join(data_path, folder,'*.jpg')
        filenames = glob(file_dir)
        images = [get_images(filename) for filename in filenames]

        mean, std = get_inception_score(images)
        print("DIR:", folder,", mean: ", str(mean),", std: ", str(std))

        with open(inv_path, "a") as inv_txt:
            inv_txt.write("\n" + folder + ", Inception Score, Mean: " + str(mean) + ", Std Dev:" + str(std))

