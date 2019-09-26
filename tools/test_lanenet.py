#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 18-5-23 上午11:33
# @Author  : MaybeShewill-CV
# @Site    : https://github.com/MaybeShewill-CV/lanenet-lane-detection
# @File    : test_lanenet.py
# @IDE: PyCharm Community Edition
"""
test LaneNet model on single image
"""
import argparse
import os.path as ops
import time
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "7"
import sys
sys.path.append('./')

import cv2
import glog as log
import matplotlib.pyplot as plt
# plt.switch_backend('agg')
import numpy as np
import tensorflow as tf

from config import global_config
from lanenet_model import lanenet
from lanenet_model import lanenet_postprocess

CFG = global_config.cfg

def init_args():
    """

    :return:
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--image_path', type=str, default='./data/tusimple_test_image/0.jpg',
                        help='The image path or the src image save dir')
    parser.add_argument('--weights_path', type=str,
                        default='./model/mobileNet_lanenet/culane_lanenet_mobilenet_v2.ckpt',
                        help='The model weights path')
    # './model/tusimple_lanenet_vgg/tusimple_lanenet_vgg.ckpt'
    # './model/mobileNet_lanenet/culane_lanenet_mobilenet_v2_changename.ckpt'
    parser.add_argument('--net_flag', type=str, default='mobilenet_v2', # vgg mobilenet_v2
                        help='Backbone Network Tag')

    return parser.parse_args()


def args_str2bool(arg_value):
    """

    :param arg_value:
    :return:
    """
    if arg_value.lower() in ('yes', 'true', 't', 'y', '1'):
        return True

    elif arg_value.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Unsupported value encountered.')


def minmax_scale(input_arr):
    """

    :param input_arr:
    :return:
    """
    min_val = np.min(input_arr)
    max_val = np.max(input_arr)

    output_arr = (input_arr - min_val) * 255.0 / (max_val - min_val)

    return output_arr


def test_lanenet(image_path, weights_path, net_flag):
    """

    :param image_path:
    :param weights_path:
    :param net_flag
    :return:
    """
    assert ops.exists(image_path), '{:s} not exist'.format(image_path)

    log.info('Start reading image and preprocessing')
    t_start = time.time()
    image = cv2.imread(image_path, cv2.IMREAD_COLOR)
    image_vis = image
    image = cv2.resize(image, (512, 256), interpolation=cv2.INTER_LINEAR) # W521 x H256
    if net_flag == 'vgg':
        image = image / 127.5 - 1.0 # 归一化到 -1,1
    elif net_flag == 'mobilenet_v2':
        image = image - [103.939, 116.779, 123.68]
    log.info('Image load complete, cost time: {:.5f}s'.format(time.time() - t_start))

    input_tensor = tf.placeholder(dtype=tf.float32, shape=[1, 256, 512, 3], name='input_tensor')

    net = lanenet.LaneNet(net_flag='vgg', phase='test')
    binary_seg_ret, instance_seg_ret = net.inference(input_tensor=input_tensor, name='lanenet_model')

    postprocessor = lanenet_postprocess.LaneNetPostProcessor()

    saver = tf.train.Saver()

    # Set sess configuration
    # ============================== config GPU
    sess_config = tf.ConfigProto()
    sess_config.gpu_options.per_process_gpu_memory_fraction = CFG.TEST.GPU_MEMORY_FRACTION
    sess_config.gpu_options.allow_growth = CFG.TRAIN.TF_ALLOW_GROWTH
    sess_config.gpu_options.allocator_type = 'BFC' # TensorFlow内存管理bfc算法
    # ==============================
    sess = tf.Session(config=sess_config)

    with sess.as_default():

        saver.restore(sess=sess, save_path=weights_path)

        t_start = time.time()
        binary_seg_image, instance_seg_image = sess.run(
            [binary_seg_ret, instance_seg_ret],
            feed_dict={input_tensor: [image]}
        )
        # np.savez('seg_iamge',binary_seg_image=binary_seg_image,instance_seg_image =instance_seg_image)
        t_cost = time.time() - t_start
        log.info('Single imgae inference cost time: {:.5f}s'.format(t_cost))

        postprocess_result = postprocessor.postprocess(
            binary_seg_result=binary_seg_image[0],
            instance_seg_result=instance_seg_image[0],
            source_image=image_vis
        )
        mask_image = postprocess_result['mask_image']

        for i in range(CFG.TRAIN.EMBEDDING_FEATS_DIMS):
            instance_seg_image[0][:, :, i] = minmax_scale(instance_seg_image[0][:, :, i])
        embedding_image = np.array(instance_seg_image[0], np.uint8)
        print('============================================')
        plt.figure('mask_image')
        plt.imshow(mask_image[:, :, (2, 1, 0)])
        plt.figure('src_image')
        plt.imshow(image_vis[:, :, (2, 1, 0)])
        plt.figure('instance_image')
        plt.imshow(embedding_image[:, :, (2, 1, 0)])
        plt.figure('binary_image')
        plt.imshow(binary_seg_image[0] * 255, cmap='gray')
        plt.show()

        # cv2.imwrite('instance_mask_image.png', mask_image)
        # cv2.imwrite('source_image.png', postprocess_result['source_image'])
        # cv2.imwrite('binary_mask_image.png', binary_seg_image[0] * 255)

    sess.close()

    return


if __name__ == '__main__':
    """
    test code
    """
    # init args
    args = init_args()

    test_lanenet(args.image_path, args.weights_path, args.net_flag)
