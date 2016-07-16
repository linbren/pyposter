# PyPoster：轻量级的博客发布小工具
## 介绍
**PyPoster** 是一个采用 Python 3.5 编写的博客离线发布小工具，GUI 采用 `tkinter` 框架构建，所以可以在安装了 Python 运行环境的多种平台下使用它。`PyPoster` 目前还只是一个简单的原型，只支持 `Wordpress` 博客。

## 为什么会有 PyPoster
以前在 Windows 平台下，会经常使用 WizNote 写东西，然后使用 WizNote 的博客发布功能进行发布。但是切换到 Ubuntu 或者 Mac OS 后，就只能使用 WizNote 的开源版本了，可惜那个版本没有 Windows 平台那么强大，所以也没有博客发布工具。所以就一直希望能有这么一款小工具，可以协助发布离线编写的文章。一开始是想找找有没有别人写的类似的小工具，但是并没有发现。由于平时主要使用 Ubuntu 系统，所以想找到一款可以在这个平台上运行又符合需求的小工具着实不易。于是 **PyPoster** 就诞生了。

## 功能支持
**Note**: 目前还是原型，所以只支持少量暂时用到的功能。

- [x] 支持 Markdown 格式的博客发布功能（没有像 WizNote 那样可将 Markdown 文档选渲染后再发布的功能，主要是想用网站自定义的 Markdown 主题）；
- [x] 支持媒体文件（主要是图片）的自动上传功能，会自动依附到相应的博客中；

## 安装 PyPoster
- pass

## 使用流程
1. 创建一个目录，专门用于放置离线博客文档和相应的媒体文件。
2. 使用你喜欢的编辑器创建并编辑你的博客文档（我喜欢使用 gedit 写 Markdown 博客）；如果期间需要插入图片，只需要将图片命名后存放在与博客文档同目录下的`media`子目录，并在文档中链接到图片即可（博客发布后会自动将图片链接替换成实际的 URL）。
3. 当你完成博客后，类似的目录结构应该和下面的类似：

    ```
    post_foo/（存放博客文档和媒体资源的目录）
    ├── blog.md（博客文档，可以使用你自己的文章标题命令）
    └── media（存放你在博客中引用的资源文件，如图片）
        └── foo.png （图片文件）
    ```

4. 运行**PyPoster**，打开存放博客的目录（如例子中给出的 `post_foo` 目录），然后根据提示，填写相应的信息后，点击确定即可。

![插图](tests/screenshots/pyposter_gui.png)

## 依赖
- [python-wordpress-xmlrpc](https://github.com/maxcutler/python-wordpress-xmlrpc)

## 贡献
- 可以提交 issue，帮助改进，谢谢；
- 可以根据需要，扩展功能；
- 如果有更好的类似工具，请推荐给我，多谢啦！

## 许可
Licensed under the [MIT](LICENSE.md) license. 
