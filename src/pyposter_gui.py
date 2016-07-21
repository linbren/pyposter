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
import webbrowser
from tkinter import Frame, LabelFrame, OptionMenu, Listbox, Scrollbar, Button, Entry, Label, Tk, StringVar, Radiobutton, \
    TclError
from tkinter.constants import *
from tkinter.scrolledtext import ScrolledText
from tkinter.ttk import Treeview, Style
from tkinter.messagebox import showinfo, showerror, askyesno
from tkinter.filedialog import askopenfilename
from utils import config_logger
from pyposter import PyPoster, PYPOSTER_PATH, LOG_PATH, ServerConfig, load_server_config, save_server_config
import logging
import threading

sys.path.append(PYPOSTER_PATH)

# 字体配置
FONT_DEFAULT = ('', 12, 'normal')
FONT_LOG = ('', 12, 'normal')


class OutputFrame(LabelFrame):
    def __init__(self, master=None, text="日志输出", cnf={}, **kw):
        super().__init__(master, cnf, **kw)
        self._output = ScrolledText(self, font=FONT_LOG, fg='blue')
        self._output.pack(fill=BOTH, expand=YES, padx=5)
        self.config(text=text, font=FONT_DEFAULT, padx=5)
        self.pack(side=RIGHT, fill=Y, expand=YES, padx=5, pady=5)

    def write(self, text):
        # self._output.config(state=NORMAL)
        self._output.insert(END, '{}'.format(text))
        self._output.see(END)
        # self._output.config(state=DISABLED)

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
        self._post_path = StringVar(self)
        self._publish_status = StringVar(self)
        self._category_name = StringVar(self)
        self._pyposter = None
        self._categories = None
        self._make_widgets()
        self._load_config()
        self.pack(fill=Y, expand=YES, padx=5, pady=5, side=LEFT)
        self._center_window()
        self.master.protocol('WM_DELETE_WINDOW', self._on_closing)

    def _make_widgets(self):
        # 左边为功能区，右边为日志显示区
        # 分开布局
        self._function_frame = Frame(self)
        self._function_frame.pack(side=LEFT, fill=Y)

        self._make_post_info_frame()
        self._make_server_frame()
        self._make_publish_status_frame()
        self._make_options_frame()

        # 三个按钮
        btn_frm = Frame(self._function_frame)
        btn_frm.pack(side=BOTTOM, fill=X)

        # TO-DO: 添加按钮
        buttons = [
            ('添加', self._add_post_path, LEFT),
            ('载入', self._load_post, LEFT),
            ('确认', self._confirm, RIGHT)
        ]

        for col, btn in enumerate(buttons):
            Button(btn_frm, text=btn[0], font=FONT_DEFAULT, command=btn[1]).pack(fill=X, side=btn[2], padx=5, pady=5)

        # 日志显示
        self._output_frame = OutputFrame(self)

        # 重定向输出流
        sys.stderr = self._output_frame
        sys.stdout = self._output_frame

    def _make_options_frame(self):
        # 选项
        options_frm = LabelFrame(self._function_frame, text='选项', font=FONT_DEFAULT)
        options_frm.pack(fill=X, pady=5)
        # 博客标签
        Label(options_frm, text='标签 (逗号分隔)：', font=FONT_DEFAULT).grid(row=0, column=0, sticky=W, padx=5)
        Entry(options_frm, textvariable=self._tags, font=FONT_DEFAULT, width=30).grid(row=0, column=1, columnspan=2,
                                                                                      sticky=E, padx=5)
        # 博客分类
        Label(options_frm, text='博客分类：', font=FONT_DEFAULT).grid(row=1, column=0, sticky=W, padx=5)
        Entry(options_frm, textvariable=self._category_name, width=19, font=FONT_DEFAULT).grid(row=1, column=1, sticky=E)
        Button(options_frm, text='获取分类', font=FONT_DEFAULT, command=self._update_category).grid(row=1,
                                                                                                column=2,
                                                                                                sticky=E,
                                                                                                padx=5)
        cat_frm = Frame(options_frm)
        cat_frm.grid(row=2, column=0, columnspan=3, sticky=W, padx=5, pady=2)

        vs = Scrollbar(cat_frm)
        vs.pack(side=RIGHT, fill=Y)
        self._categories = Treeview(cat_frm, yscroll=vs.set)
        self._categories.bind('<ButtonRelease>', self._on_item_select)
        vs.config(command=self._categories.yview)
        self._categories.heading('#0', text='选择博客分类')
        self._categories.column('#0', width=400)
        s = Style()
        s.configure('.', font=FONT_DEFAULT)
        self._categories.pack(side=LEFT, fill=BOTH, expand=YES)

    def _make_operations_frame(self):
        # 发布操作
        # 自动，新建博客，编辑博客，新建页面，编辑页面
        pass

    def _make_publish_status_frame(self):
        # 发布状态
        status_frame = LabelFrame(self._function_frame, text='发布状态', font=FONT_DEFAULT)
        status_frame.pack(fill=X, pady=5)

        Radiobutton(status_frame, variable=self._publish_status, text='草稿',
                    value='draft', font=FONT_DEFAULT).pack(side=LEFT)

        Radiobutton(status_frame, variable=self._publish_status, text='发布',
                    value='publish', font=FONT_DEFAULT).pack(side=LEFT)

        self._publish_status.set('draft')

    def _make_server_frame(self):
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
                                                                                                    column=1, sticky=E,
                                                                                                    padx=5, pady=2)

    def _make_post_info_frame(self):
        # 博客标题
        info_frm = LabelFrame(self._function_frame, text='博客信息', font=FONT_DEFAULT)
        info_frm.pack(side=TOP, fill=X, pady=5)

        rows = [
            ('博客路径：', self._post_path),
            ('博客标题：', self._post_title)
        ]

        for index, row in enumerate(rows):
            Label(info_frm, text=row[0], font=FONT_DEFAULT).grid(row=index, column=0, sticky=W,
                                                                 padx=5, pady=2)
            Entry(info_frm, textvariable=row[1], font=FONT_DEFAULT, width=35).grid(row=index, column=1, sticky=E,
                                                                                   padx=5, pady=2)

    def _center_window(self, width=850, height=610):
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width / 2) - (width / 2)
        y = (screen_height / 2) - (height / 2)
        self.master.geometry('%dx%d+%d+%d' % (width, height, x, y))

    def _add_post_path(self):
        self._post_path.set(askopenfilename(title='添加博客路径...'))
        self._load_post()

    def _load_post(self):
        post_path = self._post_path.get()

        if not os.path.exists(post_path):
            logging.error('不存在的文件： {}'.format(post_path))
            showerror('错误！', '不存在的文件：{}'.format(post_path))
            return

        post_dir, post_filename = os.path.split(post_path)

        # 添加一个恰当的标题
        self._post_title.set(os.path.splitext(post_filename)[0])

        # 获取目录下的配置文件（如果没有，则无需加载）
        post_conf_path = os.path.join(post_dir, 'post.conf')
        if not os.path.exists(post_conf_path):
            logging.warning('博客配置文件未找到，采用默认配置！')
            return

        # 加载配置文件，读取相关信息，并填充到相应的控件中
        conf = json.load(open(post_conf_path))
        if conf:
            # 下面的做法可以防止已经填写好的信息被空的内容替代，那样是不好的。
            self._post_title.set(conf['title']) if conf['title'] != '' else None
            self._tags.set(conf['tags']) if conf['tags'] != '' else None
            self._category_name.set(conf['category']) if conf['category'] != '' else None
            self._publish_status.set(conf['status']) if conf['status'] != '' else None

    def _confirm(self):
        if not self._pyposter:
            self._init_pyposter()

        if self._pyposter:
            if not all([self._post_title.get(),
                        self._post_path.get()]):
                showerror('提示', '博客博客信息不完整，至少需要合法的博客路径！')
                return
            # 在后台线程中执行操作
            threading.Thread(target=self._post, daemon=True).start()

    def _post(self):
        link = self._pyposter.post(self._post_title.get(),
                                   self._category_name.get(),
                                   self._tags.get(),
                                   self._post_path.get(),
                                   self._publish_status.get())
        if link != '' and askyesno('提示', '博客发布成功，需要在浏览器中打开吗？'):
            webbrowser.open(link)

    def _update_category(self):
        if not self._pyposter:
            self._init_pyposter()

        if self._pyposter:
            # 删除旧的分类信息
            self._categories.delete(*self._categories.get_children())
            cates = self._pyposter.get_categories()
            logging.info('成功获取到分类：{} 个。'.format(len(cates)))
            while len(cates) > 0:
                # 每次成功添加一个节点，就把它从原来的表中移除，这样下次遍历时就会更快点，直到最后一个节点添加完毕。
                for cate in cates:
                    try:
                        if cate.parent == '0':
                            self._categories.insert('', 'end', cate.id, text=cate.name, open=True)
                        else:
                            self._categories.insert(cate.parent, 'end', cate.id, text=cate.name, open=True)
                        cates.remove(cate)
                    except TclError:
                        pass

    def _init_pyposter(self):
        if not self._is_server_info_valid():
            logging.error('服务器信息填写不完整！')
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
        server_config = load_server_config()
        if server_config:
            assert isinstance(server_config, ServerConfig)
            self._rpc_addr.set(server_config.rpc_address)
            self._username.set(server_config.username)
            self._password.set(server_config.password)

    def _save_config(self):
        save_server_config(ServerConfig(self._rpc_addr.get(),
                                        self._username.get(),
                                        self._password.get()))

    def _on_closing(self):
        if self._is_server_info_valid():
            self._save_config()
        self.quit()

    def _get_selected_category(self):
        try:
            focus_item = self._categories.focus()
            return self._categories.item(focus_item)['text']
        except: return ''

    def _on_item_select(self, event):
        # fix bug here
        cat = self._get_selected_category()
        if cat != '':
            self._category_name.set(cat)


def main():

    app = Tk()
    app.title('PyPoster, 博客发布小工具 (By Christopher L)。')
    app.resizable(width=False, height=False)

    # 左边是功能区
    PyPosterGUI(app)

    config_logger(LOG_PATH)
    logging.info('欢迎使用 PyPoster!')
    logging.info('详细的帮助文档请参见 README.md。')
    logging.info('Bug 反馈请访问项目主页：https://github.com/chrisleegit/pyposter。')
    logging.info('')
    app.mainloop()


if __name__ == '__main__':
    main()
