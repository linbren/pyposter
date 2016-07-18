#!/usr/bin/env python3
# -*-coding: utf-8-*-
# Author : Chris
# Blog   : http://post.chriscabin.com
# GitHub : https://www.github.com/chrisleegit
# File   : pyposter.py
# Date   : 16-7-16
# Version: 0.1
# Description: PyPoster
import logging
import mimetypes
import os
import re
from wordpress_xmlrpc import *
from wordpress_xmlrpc.methods.media import UploadFile
from wordpress_xmlrpc.methods.posts import NewPost, EditPost, GetPost
from wordpress_xmlrpc.methods.users import GetUserInfo
from wordpress_xmlrpc.methods.taxonomies import *
from utils import config_logger, get_checksum, get_text_checksum
from json import load, dump
from pickle import load as p_load, dump as p_dump
import sys
from Crypto.Cipher import AES
from hashlib import md5


# 获取脚本所在目录
PYPOSTER_PATH = os.path.split(os.path.realpath(__file__))[0]

sys.path.append(PYPOSTER_PATH)

# PyPoster 服务器配置文件路径
SERVER_CONF_PATH = os.path.join(PYPOSTER_PATH, 'conf.pkl')

# 指定日志输出路径
LOG_PATH = os.path.join(PYPOSTER_PATH, 'log.txt')


class ServerConfig(object):
    def __init__(self, rpc_address, username, password):
        self._rpc_address = rpc_address
        self._username = username
        self._password = self._encrypt(password)

    @staticmethod
    def _encrypt(password):
        return AES.new(b'pyposter' * 2, AES.MODE_CFB, b'pyposter' * 2).encrypt(password)

    @staticmethod
    def _decrypt(password):
        return AES.new(b'pyposter' * 2, AES.MODE_CFB, b'pyposter' * 2).decrypt(password)

    @property
    def rpc_address(self):
        return self._rpc_address

    @property
    def username(self):
        return self._username

    @property
    def password(self):
        return (self._decrypt(self._password)).decode()

    def __str__(self):
        return 'rpc: {}\n' \
               'username: {}\n' \
               'password: {}\n'.format(self._rpc_address, self._username, self._password)


def load_server_config():
    # logging.info('Load pyposter config')
    if os.path.exists(SERVER_CONF_PATH):
        with open(SERVER_CONF_PATH, 'rb') as f:
            return p_load(f)


def save_server_config(config):
    # logging.info('Save pyposter config')
    if not config:
        return

    with open(SERVER_CONF_PATH, 'wb') as f:
        p_dump(config, f)


class PyPoster(object):
    def __init__(self, rpc_address, username, password):
        self._rpc_addr = rpc_address
        self._username = username
        self._password = password
        # 查找 markdown 中所有引用的图片
        self._image_re = re.compile(r'(!\[.*?\]\()(.+?)(\))')
        self._client = None
        self._post_conf = None
        self._login()

    def _login(self):
        try:
            self._client = Client(self._rpc_addr, self._username, self._password)
            print('登录成功！你好，{}！'.format(self._client.call(GetUserInfo())))
        except Exception as e:
            logging.error(str(e))
            sys.exit(1)

    def get_category_names(self):
        if isinstance(self._client, Client):
            return list(map(lambda x: x.name,
                            self._client.call(GetTerms('category'))))

    def get_post(self, post_id):
        try:
            return self._client.call(GetPost(post_id))
        except Exception as e:
            logging.error(str(e))

    def post(self, title, category, tags, post_path):

        post_path = os.path.abspath(post_path)
        post_dir = os.path.split(post_path)[0]

        if not os.path.exists(post_path):
            logging.error('不存在的文件或目录：{}'.format(post_path))
            return

        # 切换工作目录，哈哈，这个是必须这样的
        old_cwd = os.getcwd()
        os.chdir(post_dir)

        # 读取博客内容
        content = open(post_path).read()
        if not content:
            return

        logging.info('准备发布博客：{}，请稍等...'.format(title))

        # 加载博客配置
        self._load_post_conf(post_dir)

        # 处理博客中所有引用的本地图片
        posted_images = self._process_images(content)

        # 处理博客文档内容
        content = self._process_post_content(content, posted_images)

        # 检查是否确实需要发布
        if not self._is_post_modified(title, category, tags, content):
            logging.warning('博客信息未更改，拒绝发布！再见～')
            return None

        # 构建博客
        p = self._build_post(title, category, tags, content)

        if self._has_post():
            # 博客已经发布过了，此时只要编辑即可
            logging.info('开始编辑博客额：{}({})'.format(title, self._post_conf['post_id']))
            p.id = self._post_conf['post_id']
            self._client.call(EditPost(self._post_conf['post_id'], p))
        else:
            logging.info('开始新建博客：{}'.format(title))
            p.id = self._client.call(NewPost(p))
            self._post_conf['post_id'] = p.id

        # 记录下文章的标题，分类和标签信息，可能会用到
        self._post_conf['category'] = category
        self._post_conf['tags'] = tags
        self._post_conf['title'] = title
        self._post_conf['checksum'] = get_text_checksum(content)

        # 最后要保存配置
        self._save_post_conf(post_dir)
        logging.info('博客发布完成！')

        # 切换回原来的工作目录
        os.chdir(old_cwd)

        return p.id

    @staticmethod
    def _process_post_content(content, posted_images):
        # 将内容中所有的图片地址替换成实际的url
        logging.info('处理博客内容...')
        for x in posted_images:
            content = content.replace(x[0], x[-1])

        return content

    def _process_images(self, content):
        # 提取文中引用到的图片
        images = self._get_all_valid_images(content)

        same_images = list()

        # 上传图片，成功上传图片后记录图片的md5值和实际URL
        for image in images:
            # 过滤重复图片，避免重复上传（使用md5值)
            checksum = get_checksum(image)
            if checksum not in self._post_conf['posted_images']:
                # 开始上传图片
                url = self._upload_image(image)
                if url:
                    # 添加到已经上传的列表
                    self._post_conf['posted_images'][checksum] = [image, url]
            else:
                # 检查是不是有可能存在不同路径但实际是同一张图片的情况
                posted_image = self._post_conf['posted_images'][checksum]
                if image != posted_image[0]:
                    logging.warning('发现相同的图片文件：{} 与 {} 的 HASH 值相同！将会自动替换为同一 URL！'.format(image, posted_image[0]))
                    same_images.append([image, posted_image[-1]])

        same_images.extend(list(self._post_conf['posted_images'].values()))
        return same_images

    def _build_post(self, title, category, tags, content):
        logging.info('构建博客：{}'.format(title))
        post = WordPressPost()
        post.title = title
        post.content = content

        # 发布状态
        post.post_status = 'draft'
        self._add_category(category, post)
        self._add_tags(post, tags)

        return post

    def _add_category(self, category, post):
        # 添加目录
        logging.info('添加目录：{}'.format(category))
        all_cats = self._client.call(GetTerms('category'))
        post_category = [x for x in all_cats if x.name == category]
        post.terms.append(post_category[0]) if len(post_category) == 1 else None

    def _add_tags(self, post, tags):
        # 添加标签
        all_tags = self._client.call(GetTerms('post_tag'))
        tags_text = map(lambda x: x.strip(), tags.split(','))
        for tag_text in tags_text:
            # Bug fix: 空的 tag 不要添加
            if tag_text == '':
                continue

            logging.info('添加标签：{}'.format(tag_text))
            # 找 tag_text， 如果存在则无需创建，否则需要创建新的tag
            tag = [x for x in all_tags if x.name == tag_text]

            if len(tag) == 1:
                post.terms.append(tag[0])
            else:
                # 新建标签
                term = WordPressTerm()
                term.taxonomy = 'post_tag'
                term.name = tag_text
                term.id = self._client.call(NewTerm(term))
                post.terms.append(term)

    def _has_post(self):
        # 如果存在，则返回post_id
        return True if self._post_conf['post_id'] else False

    def _upload_image(self, imagename):
        # 准备数据
        data = dict()
        # 获取真实的文件名称，带有后缀名，不需要目录
        data['name'] = os.path.split(imagename)[-1]
        data['type'] = mimetypes.guess_type(imagename)[0]
        data['overwrite'] = 'false'
        with open(imagename, 'rb') as img:
            data['bits'] = xmlrpc_client.Binary(img.read())

        logging.info('上传图片：{}'.format(imagename))
        x = self._client.call(UploadFile(data))
        return x['url'] if x else None

    def _load_post_conf(self, post_dir):
        # 在博客路径下查找并加载配置文件，没有会自动生成
        conf_path = os.path.join(post_dir, 'post.conf')

        logging.info('加载博客配置文件{}'.format(conf_path))

        if os.path.exists(conf_path):
            self._post_conf = load(open(conf_path))
        else:
            self._post_conf = {'post_id': None, 'posted_images': dict(),
                               'category': '', 'tags': '', 'title': '', 'checksum': ''}

    def _save_post_conf(self, post_dir):
        logging.info('保存博客配置到文件：{}'.format(os.path.join(post_dir, 'post.conf')))
        if self._post_conf:
            with open(os.path.join(post_dir, 'post.conf'), 'w') as f:
                dump(self._post_conf, f, indent=4)

    def _get_all_valid_images(self, content):
        assert isinstance(content, str)
        # 查找博客文档中所有引用的本地图片，会验证图片的有效性
        images = self._image_re.findall(content)
        result = [x[1] for x in images if os.path.exists(x[1])]
        return result

    def _is_post_modified(self, title, category, tags, content):
        # 检查博客是否发生变动了
        if title != self._post_conf['title']:
            return True

        if category != self._post_conf['category']:
            return True

        if tags != self._post_conf['tags']:
            return True

        if get_text_checksum(content) != self._post_conf['checksum']:
            return True


def main():
    config_logger()

    # 命令行模式
    from getpass import getpass
    print('>{} 欢迎使用 PyPoster！ {}<'.format('*' * 10, '*' * 10))

    wp = None

    # 如果存在配置文件，则无需输入
    conf = load_server_config()
    if conf:
        if not input('检查到服务器配置，是否需要重新配置？[Y(es)/N(o)]').lower() in ('y', 'yes'):
            wp = PyPoster(conf.rpc_address, conf.username, conf.password)

    if not wp:
        xml_rpc_address = input('xmlrpc 地址：')
        username = input('用户名：')
        password = getpass('密码：')
        wp = PyPoster(xml_rpc_address, username, password)

        # 保存配置
        save_server_config(ServerConfig(xml_rpc_address, username, password))

    while True:
        if 'quit' in input('输入"quit"退出，回车键继续：'):
            break
        else:
            post_path = input('博客路径：')
            post_title = input('博客标题：')
            category = input('博客分类：')
            tags = input('博客标签（用逗号隔开多个）：')
            if input('确认发布？ [Y(es)/N(o)]').lower() in ['y', 'yes']:
                wp.post(post_title, category, tags, post_path)


if __name__ == '__main__':
    main()