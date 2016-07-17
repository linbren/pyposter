#!/usr/bin/env python3
# -*-coding: utf-8-*-
# Author : Chris
# Blog   : http://blog.chriscabin.com
# GitHub : https://www.github.com/chrisleegit
# File   : pyposter_gui.py
# Date   : 16-7-16
# Version: 0.1
# Description: pyposter_gui.

import json
import os
import sys
# from gettext import gettext as _
import webbrowser
from tkinter import Frame, LabelFrame, OptionMenu, Listbox, Scrollbar, Button, Entry, Label, Tk, StringVar, Toplevel
from tkinter.constants import *
from tkinter.scrolledtext import ScrolledText
from tkinter.messagebox import showinfo, showerror, askyesno
from tkinter.filedialog import askdirectory
from utils import config_logger
from pyposter import PyPoster, PYPOSTER_PATH, LOG_PATH, ServerConfig, load_config, save_config
import logging
import threading

sys.path.append(PYPOSTER_PATH)

# 字体配置
FONT_DEFAULT = ('', 12, 'normal')
FONT_LOG = ('', 11, 'normal')


class OutputFrame(LabelFrame):
    def __init__(self, master=None, text="日志输出", cnf={}, **kw):
        super().__init__(master, cnf, **kw)
        self._output = ScrolledText(self, font=FONT_LOG, fg='green')
        self._output.pack(fill=BOTH, expand=YES, padx=5, pady=5)
        self.config(text=text, font=FONT_DEFAULT)
        self.pack(side=RIGHT, fill=Y, expand=YES, padx=5, pady=5)

    def write(self, text):
        self._output.config(state=NORMAL)
        self._output.insert(END, '{}'.format(text))
        self._output.see(END)
        self._output.config(state=DISABLED)

    def read(self):
        pass

    def flush(self):
        pass

    def _get_line_count(self):
        return int(self._output.index(END).split('.')[0]) - 1

    def _clear(self):
        self._output.delete('1.0', 'end')


class PyPosterGUI(Frame):
    def __init__(self, master=None, cnf={}, **kwargs):
        super().__init__(master, cnf, **kwargs)
        self._function_frame = None
        self._output_frame = None
        self._tags = StringVar(self)
        self._post_title = StringVar(self)
        self._rpc_addr = StringVar(self)
        self._port = StringVar(self)
        self._username = StringVar(self)
        self._password = StringVar(self)
        self._operation = StringVar(self)
        self._blog_path = StringVar(self)
        self._category_name = StringVar(self)
        self._pyposter = None
        self._categories = None
        self.make_widgets()
        self._load_config()
        self.pack(fill=Y, expand=YES, padx=5, pady=5, side=LEFT)
        self.center_window()
        self.master.protocol('WM_DELETE_WINDOW', self._on_closing)

    def make_widgets(self):
        # 左边为功能区，右边为日志显示区
        # 分开布局
        self._function_frame = Frame(self)
        self._function_frame.pack(side=LEFT, fill=Y)

        self.make_post_info_frame()
        self.make_server_frame()
        # self.make_operations_frame()
        self.make_options_frame()

        # 三个按钮
        btn_frm = Frame(self._function_frame)
        btn_frm.pack(side=BOTTOM, fill=X)

        # TO-DO: 添加按钮
        buttons = [
            ('添加', self._add_dir, LEFT),
            ('载入', self._open_dir, LEFT),
            ('确认', self._confirm, RIGHT)
        ]

        for col, btn in enumerate(buttons):
            Button(btn_frm, text=btn[0], font=FONT_DEFAULT, command=btn[1]).pack(fill=X, side=btn[2], padx=5, pady=5)

        # 日志显示
        self._output_frame = OutputFrame(self)

        # 重定向输出流
        sys.stderr = self._output_frame
        sys.stdout = self._output_frame

    def make_options_frame(self):
        # 选项
        options_frm = LabelFrame(self._function_frame, text='选项', font=FONT_DEFAULT)
        options_frm.pack(fill=X)
        # 博客标签
        Label(options_frm, text='标签 (逗号分隔)：', font=FONT_DEFAULT).grid(row=0, column=0, sticky=W, padx=5)
        Entry(options_frm, textvariable=self._tags, font=FONT_DEFAULT, width=30).grid(row=0, column=1, columnspan=2,
                                                                                      sticky=E, padx=5)
        # 文章分类
        Label(options_frm, text='文章分类：', font=FONT_DEFAULT).grid(row=1, column=0, sticky=W, padx=5)
        Entry(options_frm, textvariable=self._category_name, width=19, font=FONT_DEFAULT).grid(row=1, column=1, sticky=E)
        Button(options_frm, text='获取分类', font=FONT_DEFAULT, command=self._update_category).grid(row=1,
                                                                                                column=2,
                                                                                                sticky=E,
                                                                                                padx=5)
        cat_frm = Frame(options_frm)
        cat_frm.grid(row=2, column=0, columnspan=3, sticky=W, padx=5, pady=2)

        vs = Scrollbar(cat_frm)
        vs.pack(side=RIGHT, fill=Y)
        self._categories = Listbox(cat_frm, width=44, font=FONT_DEFAULT, yscrollcommand=vs.set)
        self._categories.bind('<<ListboxSelect>>', self._on_item_select)
        vs.config(command=self._categories.yview)
        self._categories.pack(side=LEFT, fill=BOTH, expand=YES)

    def make_operations_frame(self):
        # 发布操作
        # 自动，新建博客，编辑博客，新建页面，编辑页面
        operations_frm = Frame(self._function_frame)
        operations_frm.pack(fill=X)
        Label(operations_frm, text='操作：', font=FONT_DEFAULT).pack(side=LEFT)
        opm = OptionMenu(operations_frm, self._operation, '自动模式', '新建博客', '编辑博客', '新建页面', '编辑页面')
        opm.config(font=FONT_DEFAULT)
        opm.pack(side=RIGHT)
        self._operation.set('自动模式')

    def make_server_frame(self):
        # 服务器信息
        server_frame = LabelFrame(self._function_frame, text='服务器信息', font=FONT_DEFAULT)
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
        info_frm = LabelFrame(self._function_frame, text='博客信息', font=FONT_DEFAULT)
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

    def center_window(self, width=850, height=520):
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.master.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def _add_dir(self):
        self._blog_path.set(askdirectory(title='添加博客目录...'))
        self._open_dir()

    def _open_dir(self):
        blog_path = self._blog_path.get()

        if not os.path.isdir(blog_path):
            logging.error('No such directory: {}'.format(blog_path))
            showerror('错误！', '不存在的目录：{}'.format(blog_path))
            return

        # 获取目录下的博客标题等信息
        blog_file = [x for x in os.listdir(blog_path)
                     if x != 'post.conf' and
                     not os.path.isdir(os.path.join(blog_path, x))]

        if len(blog_file) == 1:
            # 查看有没有配置文件
            conf = None
            post_conf_path = os.path.join(blog_path, 'post.conf')
            if os.path.exists(post_conf_path):
                with open(post_conf_path, 'r') as f:
                    conf = json.load(f)

            # 填充标题、路径、标签、分类等
            self._blog_path.set(blog_path)
            self._post_title.set(os.path.splitext(blog_file[0])[0])
            if conf:
                self._post_title.set(conf['title']) if conf['title'] != '' else None
                self._tags.set(conf['tags'])
                self._category_name.set(conf['category'])
            else:
                pass
        else:
            logging.error('Invalid blog path')
            showerror('提示', '无效的博客目录！')

    def _confirm(self):
        if not self._pyposter:
            self._init_pyposter()

        if self._pyposter:
            if not all([self._post_title.get(),
                        self._blog_path.get()]):
                showerror('提示', '博客文章信息不完整，至少需要合法的博客路径！')
                return
            # 在后台线程中执行操作
            threading.Thread(target=self._post, daemon=True).start()

    def _post(self):
        post_id = self._pyposter.post(self._post_title.get(),
                                      self._category_name.get(),
                                      self._tags.get(),
                                      self._blog_path.get())
        if post_id:
            if askyesno('提示', '文章发布成功，需要在浏览器中打开吗？'):
                x = self._pyposter.get_post(post_id)
                webbrowser.open(x.link) if x else None

    def _update_category(self):
        if not self._pyposter:
            self._init_pyposter()

        if self._pyposter:
            self._categories.delete(0, END)
            for name in self._pyposter.get_category_names():
                self._categories.insert('end', name)

    def _init_pyposter(self):
        if not self._is_server_info_valid():
            logging.error('Invalid parameters for PyPoster')
            showerror('错误！', '服务器信息填写不完整！')
        else:
            self._pyposter = PyPoster(self._rpc_addr.get(),
                                      self._username.get(),
                                      self._password.get())
            self._save_config()

    def _is_server_info_valid(self):
        return all([self._rpc_addr.get(), self._username.get(), self._password.get()])

    def _load_config(self):
        # 服务器信息
        server_config = load_config()
        if server_config:
            assert isinstance(server_config, ServerConfig)
            self._rpc_addr.set(server_config.rpc_address)
            self._username.set(server_config.username)
            self._password.set(server_config.password)

    def _save_config(self):
        save_config(ServerConfig(self._rpc_addr.get(),
                                 self._username.get(),
                                 self._password.get()))

    def _on_closing(self):
        if self._is_server_info_valid():
            self._save_config()
        self.quit()

    def _get_selected_category(self):
        try:
            return self._categories.get(self._categories.curselection())
        except: return ''

    def _on_item_select(self, event):
        self._category_name.set(self._get_selected_category())


def main():

    app = Tk()
    app.title('PyPoster，博客发布小工具')
    app.resizable(width=False, height=False)

    # 左边是功能区
    PyPosterGUI(app)

    config_logger(LOG_PATH)
    logging.info('Start pyposter...')
    app.mainloop()


if __name__ == '__main__':
    main()
