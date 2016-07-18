#!/usr/bin/env python3
# -*-coding: utf-8-*-
# Author : Chris
# Blog   : http://blog.chriscabin.com
# GitHub : https://www.github.com/chrisleegit
# File   : utils.py
# Date   : 16-7-16
# Version: 0.1
# Description: utilities here.

import logging
from hashlib import md5
import os


def config_logger(log_file='log.txt', level=logging.INFO):
    """
    日志模块配置
    """
    file_fmt = '[%(asctime)s][%(module)-s][line %(lineno)-d][%(levelname)s] %(message)s'
    datefmt = '%m-%d %H:%M:%S'

    logging.basicConfig(
        level=level,
        format=file_fmt,
        datefmt=datefmt,
        filename=log_file,
        filemode='a')

    console = logging.StreamHandler()
    console.setLevel(level)

    console_fmt = '%(message)s'
    formatter = logging.Formatter(fmt=console_fmt,
                                  datefmt=datefmt)
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)


def get_checksum(filename, blocksize=65536):
    if os.path.exists(filename):
        hasher = md5()
        with open(filename, 'rb') as f:
            buff = f.read(blocksize)
            while len(buff) > 0:
                hasher.update(buff)

                # get next block
                buff = f.read(blocksize)

        return hasher.hexdigest()


def get_text_checksum(text):
    hasher = md5()
    hasher.update(text.encode('utf-8'))
    return hasher.hexdigest()


def main():
    config_logger()
    print(get_text_checksum(open('../README.md').read()))


if __name__ == '__main__':
    main()
