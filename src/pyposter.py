#!/usr/bin/env python3
# -*-coding: utf-8-*-
# Author : Chris
# Blog   : http://blog.chriscabin.com
# GitHub : https://www.github.com/chrisleegit
# File   : pyposter.py
# Date   : 16-7-16
# Version: 0.1
# Description: PyPoster
import logging
import mimetypes
import os
from xmlrpc.client import ProtocolError
import re
from wordpress_xmlrpc import *
from wordpress_xmlrpc.methods.media import UploadFile
from wordpress_xmlrpc.methods.posts import NewPost, EditPost
from wordpress_xmlrpc.methods.taxonomies import *
from src.utils import config_logger
from json import load, dump


class PyPoster(object):
    def __init__(self, rpc_address, port, username, password):
        self._rpc_addr = rpc_address
        self._port = port
        self._username = username
        self._password = password
        # 查找 markdown 中所有引用的图片
        self._image_re = re.compile(r'(!\[.*?\]\()(.+?)(\))')

    def login(self):
        pass

    def get_categories(self):
        pass

    def post(self, title, category, tags, blog_dir):
        pass

    def _create_post(self, title, category, tags, content):
        pass

    def _upload_file(self, filename, path):
        pass

    def _get_all_images(self, content):
        assert isinstance(content, str)
        # 查找博客文档中所有的图片名称，没有引用的图片将不会上传
        return [os.path.split(x[1])[-1] for x in
                self._image_re.findall(content)]

    def _get_blog_content(self, blog_dir):
        assert isinstance(blog_dir, str) and os.path.isdir(blog_dir)

        # 获取目录下的博客文件，只能有一个文件
        # 记得把配置文件过滤掉
        blog_dir = os.path.abspath(blog_dir)
        files = [os.path.join(blog_dir, x) for x in os.listdir(blog_dir) if x != 'post.conf']

        # 只要文件，滤除目录
        files = [x for x in files if not os.path.isdir(x)]

        # 文件太多会出错
        if len(files) == 1:
            return open(files[0], 'r', encoding='utf-8').read()
        else:
            return None


class WordPressPoster(PyPoster):
    def __init__(self, rpc_address, port, username, password):
        super().__init__(rpc_address, port, username, password)
        self._client = None
        self._post_conf = None
        self.login()

    def login(self):
        try:
            self._client = Client(self._rpc_addr, self._username, self._password)
        except ProtocolError as e:
            logging.error(str(e))

    def get_categories(self):
        if isinstance(self._client, Client):
            return list(map(lambda x: x.name,
                            self._client.call(GetTerms('category'))))

    def post(self, title, category, tags, blog_dir):
        logging.info('Prepare to post: {}'.format(title))
        content = self._get_blog_content(blog_dir)
        images = self._get_all_images(content)
        image_urls = dict(zip(images, images))

        # 加载博客配置
        self._load_post_conf(blog_dir)

        # 上传图片，并获取图片的地址
        for image in images:
            if image in self._post_conf['posted_images'].keys():
                # 重复图片不再上传了
                image_urls[image] = self._post_conf['posted_images'][image]
                continue

            image_path = os.path.join(blog_dir, 'images', image)
            if os.path.exists(image_path):
                url = self._upload_image(image, image_path)
                # 上传成功的图片名称会添加到记录中，下次将不会继续上传。
                if url:
                    self._post_conf['posted_images'][image] = url
                    image_urls[image] = url

        # 将内容中所有的图片地址替换成实际的url
        logging.info('Process blog content')
        for x in image_urls.keys():
            content = content.replace('images/{}'.format(x), image_urls[x])

        p = self._build_post(title, category, tags, content)

        if self._has_post():
            # 博客已经发布过了，此时只要编辑即可
            logging.info('Edit post: {}({})'.format(title, self._post_conf['post_id']))
            self._client.call(EditPost(self._post_conf['post_id'], p))
        else:
            logging.info('New post: {}'.format(title))
            self._post_conf['post_id'] = self._client.call(NewPost(p))

        # 最后要保存配置
        self._save_post_conf(blog_dir)
        logging.info('Post operation: complete!')

    def _build_post(self, title, category, tags, content):
        logging.info('Build post: {}'.format(title))
        post = WordPressPost()
        post.title = title
        post.content = content
        post.post_status = 'publish'

        # 添加目录
        logging.info('Add category: {}'.format(category))
        all_cats = self._client.call(GetTerms('category'))
        post_category = [x for x in all_cats if x.name == category]
        post.terms.append(post_category[0]) if len(post_category) == 1 else None

        # 添加标签
        all_tags = self._client.call(GetTerms('post_tag'))
        tags_text = map(lambda x: x.strip(), tags.split(','))
        for tag_text in tags_text:
            logging.info('Add tag: {}'.format(tag_text))
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

        return post

    def _has_post(self):
        # 如果存在，则返回post_id
        return True if self._post_conf['post_id'] else False

    def _upload_image(self, imagename, path):
        # 准备数据
        data = dict()
        data['name'] = imagename
        data['type'] = mimetypes.guess_type(path)[0]
        data['overwrite'] = 'false'
        with open(path, 'rb') as img:
            data['bits'] = xmlrpc_client.Binary(img.read())

        logging.info('Upload image: {}'.format(imagename))
        x = self._client.call(UploadFile(data))
        return x['url'] if x else None

    def _load_post_conf(self, blog_path):
        logging.info('Loading post config')
        # 在博客路径下查找并加载配置文件，没有会自动生成
        conf_path = os.path.join(blog_path, 'post.conf')
        if os.path.exists(conf_path):
            self._post_conf = load(open(conf_path))
        else:
            self._post_conf = {'post_id': None, 'posted_images': dict()}

    def _save_post_conf(self, blog_path):
        logging.info('Save post config')
        if self._post_conf:
            with open(os.path.join(blog_path, 'post.conf'), 'w') as f:
                dump(self._post_conf, f, indent=4)


def interactive_mode():
    pass


def main():
    config_logger()
    pass

if __name__ == '__main__':
    main()
