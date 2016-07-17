#!/usr/bin/env python3
# -*-coding: utf-8-*-
# Author : Chris
# Blog   : http://blog.chriscabin.com
# GitHub : https://www.github.com/chrisleegit
# File   : pyposter_gui.py
# Date   : 16-7-16
# Version: 0.1
# Description: pyposter_gui.

import os
import sys
from gettext import gettext as _
from tkinter import Frame, LabelFrame, OptionMenu, Listbox, Scrollbar, Button, Entry, Label, Tk, StringVar
from tkinter.constants import *
from tkinter.messagebox import showinfo, showerror
from tkinter.filedialog import askdirectory
from utils import config_logger
from pyposter import PyPoster, PYPOSTER_PATH, LOG_PATH, Config, load_config, save_config
import logging
import threading

sys.path.append(PYPOSTER_PATH)

# 字体配置
FONT_DEFAULT = ('', 12, 'normal')


class MainWindow(Frame):
    def __init__(self, master=None, cnf={}, **kwargs):
        super(MainWindow, self).__init__(master, cnf, **kwargs)
        self._tags = StringVar(self)
        self._post_title = StringVar(self)
        self._rpc_addr = StringVar(self)
        self._port = StringVar(self)
        self._username = StringVar(self)
        self._password = StringVar(self)
        self._operation = StringVar(self)
        self._blog_path = StringVar(self)
        self._pyposter = None
        self._categories = None
        self.make_widgets()
        self._load_config()
        self.pack(fill=BOTH, expand=YES, padx=10, pady=10)
        self.center_window()

    def make_widgets(self):
        self.make_post_info_frame()
        self.make_server_frame()
        # self.make_operations_frame()
        self.make_options_frame()
        # 打开和确定
        Button(self, text='打开...', font=FONT_DEFAULT, command=self._open_dir).pack(side=LEFT, pady=5)
        Button(self, text='确定', font=FONT_DEFAULT, command=self._confirm).pack(side=RIGHT, pady=5)

    def make_options_frame(self):
        # 选项
        options_frm = LabelFrame(self, text='选项', font=FONT_DEFAULT)
        options_frm.pack(fill=X)
        # 博客标签
        Label(options_frm, text='标签 (逗号分隔)：', font=FONT_DEFAULT).grid(row=0, column=0, sticky=W, padx=5)
        Entry(options_frm, textvariable=self._tags, font=FONT_DEFAULT, width=30).grid(row=0, column=1, sticky=E, padx=5)
        # 文章分类
        Label(options_frm, text='选择文章分类：', font=FONT_DEFAULT).grid(row=1, column=0, sticky=W, padx=5)
        Button(options_frm, text='更新分类', font=FONT_DEFAULT, command=self._update_category).grid(row=1, column=1, sticky=E, padx=5)

        cat_frm = Frame(options_frm)
        cat_frm.grid(row=2, column=0, columnspan=2, sticky=W, padx=5, pady=2)

        vs = Scrollbar(cat_frm)
        vs.pack(side=RIGHT, fill=Y)
        self._categories = Listbox(cat_frm, width=44, font=FONT_DEFAULT, yscrollcommand=vs.set)
        vs.config(command=self._categories.yview)
        self._categories.pack(side=LEFT, fill=BOTH, expand=YES)

    def make_operations_frame(self):
        # 发布操作
        # 自动，新建博客，编辑博客，新建页面，编辑页面
        operations_frm = Frame(self)
        operations_frm.pack(fill=X)
        Label(operations_frm, text='操作：', font=FONT_DEFAULT).pack(side=LEFT)
        opm = OptionMenu(operations_frm, self._operation, '自动模式', '新建博客', '编辑博客', '新建页面', '编辑页面')
        opm.config(font=FONT_DEFAULT)
        opm.pack(side=RIGHT)
        self._operation.set('自动模式')

    def make_server_frame(self):
        # 服务器信息
        server_frame = LabelFrame(self, text='服务器信息', font=FONT_DEFAULT)
        server_frame.pack(fill=X, pady=5)
        # 一次创建完
        rows = [('RPC 地址：', self._rpc_addr, None),
                # ('端口：', self._port, None),
                ('用户名：', self._username, None),
                ('密码：', self._password, '*')]
        for index, row in enumerate(rows):
            Label(server_frame, text=row[0], font=FONT_DEFAULT).grid(row=index, column=0, sticky=W, padx=5, pady=2)
            Entry(server_frame, textvariable=row[1], show=row[2], font=FONT_DEFAULT, width=34).grid(row=index,
                                                                                                    column=1, sticky=E, padx=5, pady=2)

    def make_post_info_frame(self):
        # 文章标题
        info_frm = LabelFrame(self, text='博客信息', font=FONT_DEFAULT)
        info_frm.pack(side=TOP, fill=X, pady=5)

        rows = [
            ('博客目录：', self._blog_path),
            ('博客标题：', self._post_title)
        ]

        for index, row in enumerate(rows):
            Label(info_frm, text=row[0], font=FONT_DEFAULT).grid(row=index, column=0, sticky=W,
                                                                 padx=5, pady=2)
            Entry(info_frm, textvariable=row[1], font=FONT_DEFAULT, width=35).grid(row=index, column=1, sticky=E,
                                                                                   padx=5, pady=2)

    def center_window(self, width=450, height=520):
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.master.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def _open_dir(self):
        blog_path = askdirectory()

        # 获取目录下的博客标题等信息
        blog_file = [x for x in os.listdir(blog_path)
                     if x != 'post.conf' and
                     not os.path.isdir(os.path.join(blog_path, x))]

        if len(blog_file) == 1:
            self._post_title.set(os.path.splitext(blog_file[0])[0])
            self._blog_path.set(blog_path)
        else:
            logging.error('Invalid blog path')
            showerror('提示', '无效的博客目录！')

    def _confirm(self):
        if not self._pyposter:
            self._init_pyposter()

        if self._pyposter:
            self._pyposter.post(self._post_title.get(),
                                self._categories.get('active'),
                                self._tags.get(),
                                self._blog_path.get())

            showinfo('提示', '发布完成！')

    def _update_category(self):
        if not self._pyposter:
            self._init_pyposter()

        if self._pyposter:
            self._categories.delete(0, END)
            for name in self._pyposter.get_category_names():
                self._categories.insert('end', name)

    def _init_pyposter(self):
        if not all([self._rpc_addr.get(),
                    self._username.get(),
                    self._password.get()]):
            logging.error('Invalid parameters for PyPoster')
            showerror('错误！', '服务器信息填写不完整！')
        else:
            self._pyposter = PyPoster(self._rpc_addr.get(),
                                      self._username.get(),
                                      self._password.get())
            save_config(Config(self._rpc_addr.get(),
                               self._username.get(),
                               self._password.get()))

    def _load_config(self):
        config = load_config()
        if config:
            assert isinstance(config, Config)
            self._rpc_addr.set(config.rpc_address)
            self._username.set(config.username)
            self._password.set(config.password)


def main():
    config_logger(LOG_PATH)
    app = Tk()
    app.title('PyPoster，博客发布小工具')
    app.resizable(width=False, height=False)
    logging.info('Start pyposter...')
    MainWindow(app)
    app.mainloop()


if __name__ == '__main__':
    main()
