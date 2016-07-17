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


def main():
    config_logger()
    logging.info('Hello, world')


if __name__ == '__main__':
    main()
