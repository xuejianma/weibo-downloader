import hashlib
import json
import time
import os
import re
from urllib import request, parse
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from datetime import datetime, timedelta
from webdriver_manager.chrome import ChromeDriverManager



class WeiboDownloader:
    def __init__(
        self,
        username=None,
        uid=None,
        save_path_csv="./weibo_posts.csv",
        save_path_json="./weibo_posts.json",
        save_media_directory="./weibo_media/",
        enable_get_video_links=True,
        enable_get_urls=True,
        enable_fill_truncated_texts=False,
        enable_download_media_all=True,
        enable_download_media_image_only=False,
        enable_download_media_video_only=False,
        enable_download_media_overwrite=False,
        enable_simplified_json=True,
        date_from=None,
        date_to=None,
        pages=None,
        weibo_timeline_url_prefix="https://m.weibo.cn/u/",
    ):
        if not uid and not username:
            raise ValueError("Either uid or username must be specified.")
        if uid and username:
            raise ValueError("Only one of uid or username can be specified.")
        self.username = username
        self.uid = uid if uid else self.get_uid_from_username(username)
        self.save_path_csv = save_path_csv
        self.save_path_json = save_path_json
        self.save_media_directory = save_media_directory
        self.enable_download_media_all = enable_download_media_all
        self.enable_download_media_image_only = enable_download_media_image_only
        self.enable_download_media_video_only = enable_download_media_video_only
        self.enable_download_media_overwrite = enable_download_media_overwrite
        self.enable_simplified_json = enable_simplified_json
        self.verbose = not self.enable_simplified_json
        if self.enable_download_media_all and (
            self.enable_download_media_image_only
            or self.enable_download_media_video_only
        ):
            raise ValueError(
                "Enable_download_media_all cannot be True if "
                "enable_download_media_image_only or "
                "enable_download_media_video_only is True, "
                "for they are mutually exclusive."
            )
        self.enable_get_video_links = enable_get_video_links
        self.enable_get_urls = enable_get_urls
        self.enable_fill_truncated_texts = enable_fill_truncated_texts
        self.date_from = self.filter_date_format(date_from) if date_from else None
        self.date_to = self.filter_date_format(date_to) if date_to else None
        self.pages = pages
        if self.pages and (self.date_from or self.date_to):
            raise ValueError(
                "Pages option is not supported when date_from and/or date_to is "
                "specified. Please remove date range options or pages option."
            )
        self.weibo_timeline_url_prefix = weibo_timeline_url_prefix
        self.dinstict_class_names = {
            "post-whole-card": "card9",
            "weibo-text": "weibo-text",
            "time": "time",
            "media-wraps": "weibo-media-wraps",
            "post-video-main-page": "mwb-video",
            "video-page-menu-item": "vjs-menu-item",
            "video-page-video": "vjs-tech",
            "video-page-back-button": "vjs-dispose-player",
            "expand-page-back-button": "nav-left",
            "indicator-back-to-main-page": "overlay",
            "indicator-enter-expand-page": "lite-page-tab",
        }
        self.date_from_stored = None
        self.date_to_stored = None
        self.card_hashes = set()
        self.ticktok = time.time()
        self.posts = []
        self.posts_in_api_format = []

    def get_uid_from_username(self, username):
        try:
            params = {
                "queryVal": username,
                "containerid": "100103type%3D3%26q%3D" + username,
            }
            response = requests.get(
                url="https://m.weibo.cn/api/container/getIndex", params=params
            )
            return int(
                response.json()["data"]["cards"][1]["card_group"][0]["user"]["id"]
            )
        except Exception as e:
            print(
                "[Error] Please check your username and try again, or directly "
                "use UID instead of username."
            )
            raise e

    def filter_date_format(self, date):
        try:
            return datetime.strptime(date, "%Y-%m-%d").date()
        except:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD")

    def generate_hash(self, element: WebElement):
        text = element.text
        return hashlib.md5(text.encode()).hexdigest()

    def prepare_webdriver(self):
        chrome_options = Options()
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--mute-audio")
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
        except:
            self.driver = webdriver.Chrome(ChromeDriverManager().install())
        self.wait = WebDriverWait(self.driver, 30)
        self.driver.get(self.weibo_timeline_url_prefix + str(self.uid))
        self.wait.until(
            lambda driver: driver.find_element(
                By.CLASS_NAME, self.dinstict_class_names["post-whole-card"]
            )
        )

    def run(self, yield_data=False):
        # Consumes the generator to get all data
        for _ in self.run_generator(yield_data):
            pass

    def run_generator(self, yield_data=False):
        if yield_data:
            self.verbose = False
        else:
            self.verbose = True
        self.prepare_webdriver()
        self.ticktok = time.time()
        self.posts = []
        self.posts_in_api_format = []
        self.card_hashes = set()
        page_count = -1 if self.pages else 0
        if self.date_from or self.pages:
            while (self.pages and page_count < self.pages) or (
                not self.pages
                and (
                    not self.date_from_stored or self.date_from_stored >= self.date_from
                )
            ):
                if self.pages > 0:
                    page_count += 1
                if self.verbose:
                    print("Getting more posts with new scroll...")
                self.scroll_to_bottom()
                self.wait.until(
                    lambda driver: len(
                        driver.find_elements(
                            By.CLASS_NAME, self.dinstict_class_names["post-whole-card"]
                        )
                    )
                    > len(self.posts)
                )
                try:
                    new_posts = self.fetch_more_posts()
                except:
                    new_posts = self.fetch_more_posts()
                if not self.enable_simplified_json:
                    new_posts_in_api_format = self.get_posts_in_api_format(new_posts)
                    self.posts_in_api_format.extend(new_posts_in_api_format)
                if not new_posts:
                    # If no new posts are found, it means we don't have posts
                    # within the date range. Break the loop.
                    break
                self.posts.extend(new_posts)
                new_ticktok = time.time()
                if self.verbose:
                    print(
                        "Scrolled to page: {}, posts on: {}, new scroll loading time (s): {}".format(
                            str(page_count),
                            str(self.date_from_stored),
                            round(new_ticktok - self.ticktok, 2),
                        )
                    )
                if yield_data:
                    for i in range(len(new_posts)):
                        if self.enable_simplified_json:
                            yield new_posts[i]
                        else:
                            yield new_posts_in_api_format[i]
                self.save()
                self.ticktok = time.time()
        elif self.date_to:
            raise ValueError(
                "date_to is specified, but not date_from. date_from is required "
                "if date_to is specified."
            )
        else:
            # If no date_from is specified, only capture the first page.
            if self.verbose:
                print("Getting more posts with new scroll...")
            try:
                new_posts = self.fetch_more_posts()
            except:
                new_posts = self.fetch_more_posts()
            if not self.enable_simplified_json:
                new_posts_in_api_format = self.get_posts_in_api_format(new_posts)
                self.posts_in_api_format.extend(new_posts_in_api_format)
            self.posts.extend(new_posts)
            if self.verbose:
                print("Scrolled to posts on: " + str(self.date_from_stored))
            if yield_data:
                for i in range(len(new_posts)):
                    if self.enable_simplified_json:
                        yield new_posts[i]
                    else:
                        yield new_posts_in_api_format[i]
            self.save()
        if self.verbose:
            print("Finished getting posts!")
        self.close()

    def get_weibo_posts_by_name(self, username):
        self.username = username
        self.uid = self.get_uid_from_username(username)
        return self.run_generator(yield_data=True)

    def scroll_to_bottom(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def fetch_more_posts(self):
        card_mains = self.driver.find_elements(
            By.CLASS_NAME, self.dinstict_class_names["post-whole-card"]
        )
        new_posts = []
        for card_main in card_mains:
            card_main_hash = self.generate_hash(card_main)
            if card_main_hash in self.card_hashes:
                continue
            if (
                self.date_from_stored
                and self.date_from
                and self.date_from_stored < self.date_from
            ):
                return
            post_data = self.extract_post_data(card_main)
            if post_data:
                new_posts.append(post_data)
            self.card_hashes.add(card_main_hash)
        if self.enable_get_video_links:
            if self.verbose:
                print("  *Getting video links...")
            self.get_video_links(new_posts)
            if self.verbose:
                print("  *Finished getting video links!")
        if self.enable_fill_truncated_texts:
            if self.verbose:
                print("  *Filling truncated texts...")
            self.fill_truncated_texts(new_posts)
            if self.verbose:
                print("  *Finished filling truncated texts!")
        if self.enable_get_urls:
            if self.verbose:
                print("  *Getting urls...")
            self.get_urls(new_posts)
            if self.verbose:
                print("  *Finished getting urls!")
        self.download_media(new_posts)
        # self.posts.extend(new_posts)
        return new_posts

    def extract_post_data(self, card_main: WebElement):
        # Get time, and skip if out of date range
        post_time_str = card_main.find_elements(
            By.CLASS_NAME, self.dinstict_class_names["time"]
        )[0].text
        post_time = self.parse_time(post_time_str)
        # Update date_from_store if post_time's date is earlier than current date_from_stored
        if not self.date_from_stored or post_time.date() < self.date_from_stored:
            self.date_from_stored = post_time.date()
        # Update date_to_store if post_time's date is later than current date_to_stored
        if not self.date_to_stored or post_time.date() > self.date_to_stored:
            self.date_to_stored = post_time.date()
        if self.date_from and post_time.date() < self.date_from:
            return None
        if self.date_to and post_time > self.date_to:
            return None
        # Get card hash, and skip if already exists from previous scroll
        card_hash = self.generate_hash(card_main)
        weibo_divs = card_main.find_elements(
            By.CLASS_NAME, self.dinstict_class_names["weibo-text"]
        )
        # Get is_text_truncated, and external links
        is_text_truncated = False
        links = []
        for weibo_div in weibo_divs:
            weibo_div_tags = weibo_div.find_elements(By.TAG_NAME, "a")
            for weibo_div_tag in weibo_div_tags:
                if "全文" in weibo_div_tag.text:
                    is_text_truncated = True
                if "网页链接" in weibo_div_tag.text:
                    links.append(weibo_div_tag.get_attribute("href"))
        # Get text
        weibo_div_text = ""
        for weibo_div in weibo_divs:
            weibo_div_text += weibo_div.text + "\n"
        # Get images
        media_wraps = card_main.find_elements(
            By.CLASS_NAME, self.dinstict_class_names["media-wraps"]
        )
        media_wrap = media_wraps[0] if media_wraps else None
        img_urls = []
        img_thumbnail_urls = []
        if media_wrap:
            img_divs = media_wrap.find_elements(By.TAG_NAME, "img")
            for img_div in img_divs:
                link = img_div.get_attribute("src")
                img_thumbnail_urls.append(link)
                link_split = link.split("/")
                for i in range(len(link_split)):
                    if link_split[i] in ["orj360", "orj480", "orj720", "orj1080"]:
                        link_split[i] = "large"
                img_urls.append("/".join(link_split))
        # Get video element hash
        video_hash = None
        if media_wrap:
            video_divs = media_wrap.find_elements(
                By.CLASS_NAME,
                self.dinstict_class_names["post-video-main-page"],
            )
            video_div = video_divs[0] if video_divs else None
            video_hash = self.generate_hash(video_div) if video_div else None
        post_data = {
            "username": self.username if self.username else "",
            "uid": self.uid,
            "text": weibo_div_text,
            "time": str(post_time),
            "thumbnail_images": img_thumbnail_urls,
            "images": img_urls,
            "video": None,
            "links": links,
            "url": None,
            "tracking_params": {
                "is_text_truncated": is_text_truncated,
                "hash": card_hash,
            },
        }
        if img_urls:
            post_data["images"] = img_urls
        if video_hash:
            post_data["tracking_params"]["video_hash"] = video_hash
        return post_data

    def get_video_links(self, posts):
        for post in posts:
            if "video_hash" in post["tracking_params"]:
                card_videos = self.driver.find_elements(
                    By.CLASS_NAME, self.dinstict_class_names["post-video-main-page"]
                )
                for card_video in card_videos:
                    if (
                        self.generate_hash(card_video)
                        == post["tracking_params"]["video_hash"]
                    ):
                        self.click(card_video)
                        self.wait.until(
                            lambda driver: driver.find_element(
                                By.CLASS_NAME,
                                self.dinstict_class_names["video-page-menu-item"],
                            )
                        )
                        all_quality_lis = self.driver.find_elements(
                            By.CLASS_NAME,
                            self.dinstict_class_names["video-page-menu-item"],
                        )
                        highest_quality_li = all_quality_lis[0]
                        self.driver.execute_script(
                            "arguments[0].click();", highest_quality_li
                        )
                        self.wait.until(
                            lambda driver: driver.find_element(
                                By.CLASS_NAME,
                                self.dinstict_class_names["video-page-video"],
                            )
                        )
                        video = self.driver.find_element(
                            By.CLASS_NAME, self.dinstict_class_names["video-page-video"]
                        )
                        video_link = video.get_attribute("src")
                        post["video"] = video_link
                        dispose_player = self.driver.find_element(
                            By.CLASS_NAME,
                            self.dinstict_class_names["video-page-back-button"],
                        )
                        self.click(dispose_player)
        return posts

    def fill_truncated_texts(self, posts):
        for post in posts:
            if post["tracking_params"]["is_text_truncated"]:
                expand_post = self.extract_post_data_from_expand(post)
                if expand_post:
                    for attr in expand_post:
                        if attr != "video":
                            if not post[attr] or post[attr] != expand_post[attr]:
                                post[attr] = expand_post[attr]
                    post["tracking_params"]["is_text_truncated"] = False
        return posts

    def get_urls(self, posts):
        for post in posts:
            if not post["url"]:
                expand_post = self.extract_post_data_from_expand(post)
                if expand_post:
                    for attr in expand_post:
                        if attr != "video":
                            if not post[attr] or post[attr] != expand_post[attr]:
                                post[attr] = expand_post[attr]
        return posts

    def scroll_to(self, element):
        self.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center', inline: 'nearest'});",
            element,
        )

    def click(self, element):
        self.driver.execute_script("arguments[0].click();", element)

    def extract_post_data_from_expand(self, post):
        card_mains = self.driver.find_elements(
            By.CLASS_NAME, self.dinstict_class_names["post-whole-card"]
        )
        for card_main in card_mains:
            if self.generate_hash(card_main) == post["tracking_params"]["hash"]:
                weibo_text = card_main.find_element(
                    By.CLASS_NAME, self.dinstict_class_names["weibo-text"]
                )
                self.click(weibo_text)
                self.wait.until(
                    lambda driver: driver.find_element(
                        By.CLASS_NAME,
                        self.dinstict_class_names["indicator-enter-expand-page"],
                    )
                )
                card_main_expanded = self.driver.find_element(
                    By.CLASS_NAME, self.dinstict_class_names["post-whole-card"]
                )
                new_post = self.extract_post_data(card_main_expanded)
                new_post["url"] = self.driver.current_url
                nav_left = self.driver.find_element(
                    By.CLASS_NAME,
                    self.dinstict_class_names["expand-page-back-button"],
                )
                self.click(nav_left)
                self.wait.until(
                    lambda driver: driver.find_element(
                        By.CLASS_NAME,
                        self.dinstict_class_names["indicator-back-to-main-page"],
                    )
                )
                return new_post

    def parse_time(self, time_str):
        """
        The time has 5 possible formats:
        1. "刚刚"
        2. "n分钟前"
        3. “n小时前”
        4. “昨天 hh:mm”
        5. "mm-dd hh:mm"
        6. "yyyy-mm-dd hh:mm"
        Need to parse them into standard datetime format.
        """
        if "刚刚" in time_str:
            return datetime.now().replace(second=0, microsecond=0)
        elif "分钟前" in time_str:
            minutes = int(time_str.split("分钟前")[0])
            return datetime.now().replace(second=0, microsecond=0) - timedelta(
                minutes=minutes
            )
        elif "小时前" in time_str:
            hours = int(time_str.split("小时前")[0])
            return datetime.now().replace(second=0, microsecond=0) - timedelta(
                hours=hours
            )
        elif "昨天" in time_str:
            time_str = (
                str(datetime.now().date()) + " " + time_str.split("昨天")[1].strip()
            )
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M") - timedelta(days=1)
        elif time_str.count("-") == 1:
            time_str = str(datetime.now().year) + "-" + time_str
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        else:
            if ":" not in time_str:
                time_str = time_str + " 00:00"
            return datetime.strptime(time_str, "%Y-%m-%d %H:%M")

    def save_json(self):
        if self.enable_simplified_json:
            posts_json = json.dumps(self.posts, indent=4, ensure_ascii=False)
        else:
            posts_json = json.dumps(
                self.posts_in_api_format, indent=4, ensure_ascii=False
            )
        with open(self.save_path_json, "w", encoding="utf-8") as f:
            f.write(posts_json)

    def save_csv(self):
        with open(self.save_path_csv, "w", encoding="utf-8") as f:
            f.write("username,uid,text,time,images,video,links,url\n")
            for post in self.posts:
                f.write(
                    '"{}","{}","{}","{}","{}","{}","{}","{}"\n'.format(
                        post["username"],
                        post["uid"],
                        post["text"],
                        post["time"],
                        "\n".join(post["images"]),
                        post["video"] if post["video"] else "",
                        "\n".join(post["links"]),
                        post["url"] if post["url"] else "",
                    )
                )

    def save(self):
        if self.save_path_json:
            self.save_json()
            if self.verbose:
                print("Data saved to: " + self.save_path_json)
        if self.save_path_csv:
            self.save_csv()
            if self.verbose:
                print("Data saved to: " + self.save_path_csv)
        if not self.save_path_json and not self.save_path_csv:
            if self.verbose:
                print("No save path specified, not saving.")
        else:
            if self.verbose:
                print("\n")

    def download(self, link, file_path):
        """
        Download a file from a link.
        """
        if self.enable_download_media_overwrite or not os.path.exists(file_path):
            request.urlretrieve(link, filename=file_path)
            return {"status": "success"}
        else:
            return {"status": "file already exists"}

    def download_media(self, posts):
        download_logged = False
        some_media_exists = False
        if not os.path.exists(self.save_media_directory):
            os.mkdir(self.save_media_directory)
        for post in posts:
            prefix = self.get_download_filename_prefex(post)
            if self.enable_download_media_all or self.enable_download_media_image_only:
                if post["images"]:
                    if not download_logged:
                        if self.verbose:
                            print("  *Downloading media...")
                        download_logged = True
                    for i in range(len(post["images"])):
                        img_url = post["images"][i]
                        img_file_path = (
                            self.save_media_directory
                            + "/"
                            + prefix
                            + "_"
                            + str(i + 1)
                            + ".jpg"
                        )
                        response = self.download(img_url, img_file_path)
                        if response["status"] != "success":
                            some_media_exists = True
            if self.enable_download_media_all or self.enable_download_media_video_only:
                if post["video"]:
                    if not download_logged:
                        if self.verbose:
                            print("  *Downloading media...")
                        download_logged = True
                    video_url = post["video"]
                    video_file_path = self.save_media_directory + "/" + prefix + ".mp4"
                    self.download(video_url, video_file_path)
                    if response["status"] != "success":
                        some_media_exists = True
        if some_media_exists:
            if self.verbose:
                print("  *Some media already exist, skipped.")
        if download_logged:
            if self.verbose:
                print("  *Finished downloading media!")

    def get_download_filename_prefex(self, post):
        post_id = post["url"].split("/")[-1] if post["url"] else None
        return (
            self.sanitize_filename(post["time"][:10] + "_" + post["text"])
            + "_"
            + post_id
            if post_id
            else post["tracking_params"]["hash"]
        )

    def sanitize_filename(self, text):
        return (
            re.sub(r'[\\/*?:"<>|]', "", text)
            .replace("\n", " ")
            .replace("\r", " ")
            .replace("\t", " ")
            .replace("@", "")
            .strip()
            .replace(" ", "_")[0:25]
        )

    def remove_empty_attrs(self, d):
        """Recursively remove empty attributes from a dictionary."""
        if isinstance(d, dict):
            cleaned_dict = {
                key: self.remove_empty_attrs(value)
                for key, value in d.items()
                if value is not None
            }
            # Remove keys whose values became empty dictionaries after cleaning
            return {
                k: v
                for k, v in cleaned_dict.items()
                if v or isinstance(v, (int, float, bool))
            }
        elif isinstance(d, list):
            return [self.remove_empty_attrs(item) for item in d if item is not None]
        else:
            return d

    def get_posts_in_api_format(self, posts):
        ret = []
        for post in posts:
            video_attr_name = (
                parse.parse_qs(parse.urlparse(post["video"]).query)["label"][0] + "_mp4"
                if post["video"]
                else None
            )
            ret.append(
                {
                    "scheme": post["url"],
                    "mblog": {
                        "created_at": post["time"],
                        "id": post["url"].split("/")[-1] if post["url"] else None,
                        "text": post["text"],
                        "screen_name": post["username"],
                        "user": {
                            "id": post["uid"],
                        },
                        "pics": [
                            {"url": img_thumbnail_url, "large": {"url": img_url}}
                            for img_thumbnail_url, img_url in zip(
                                post["thumbnail_images"], post["images"]
                            )
                        ],
                        "page_info": {
                            "urls": {},
                        },
                    },
                }
            )
            if post["video"]:
                ret[-1]["mblog"]["page_info"]["urls"][video_attr_name] = post["video"]
        ret = self.remove_empty_attrs(ret)
        return ret

    def close(self):
        self.driver.quit()


def get_weibo_posts_by_name(
    username="来去之间",
    uid=None,
    save_path_csv="./weibo_posts.csv",
    save_path_json="./weibo_posts.json",
    save_media_directory="./weibo_media/",
    enable_get_video_links=True,
    enable_get_urls=True,
    enable_fill_truncated_texts=False,
    enable_download_media_all=True,
    enable_download_media_image_only=False,
    enable_download_media_video_only=False,
    enable_download_media_overwrite=False,
    enable_simplified_json=True,
    date_from=None,
    date_to=None,
    pages=None,
    weibo_timeline_url_prefix="https://m.weibo.cn/u/",
):
    weibo_downloader = WeiboDownloader(
        username=username,
        uid=uid,
        save_path_csv=save_path_csv,
        save_path_json=save_path_json,
        save_media_directory=save_media_directory,
        enable_get_video_links=enable_get_video_links,
        enable_get_urls=enable_get_urls,
        enable_fill_truncated_texts=enable_fill_truncated_texts,
        enable_download_media_all=enable_download_media_all,
        enable_download_media_image_only=enable_download_media_image_only,
        enable_download_media_video_only=enable_download_media_video_only,
        enable_download_media_overwrite=enable_download_media_overwrite,
        enable_simplified_json=enable_simplified_json,
        date_from=date_from,
        date_to=date_to,
        pages=pages,
        weibo_timeline_url_prefix=weibo_timeline_url_prefix,
    )
    return weibo_downloader.get_weibo_posts_by_name(username)
