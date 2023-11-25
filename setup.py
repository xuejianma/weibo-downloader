from setuptools import setup

setup(
    name="weibo-downloader",
    version="0.1.0",
    description="Download weibo posts and media including texts, images and videos.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Xuejian Ma",
    author_email="Xuejian.Ma@gmail.com",
    url="https://github.com/xuejianma/weibo-downloader",
    license="MIT",
    packages=["weibo_downloader"],
    keywords=["weibo", "downloader", "scraper", "crawler", "video", "image"],
    test_suite="tests",
    install_requires=[
        "requests",
        "selenium",
        "webdriver-manager",
    ],
)
