# Weibo Downloader

## Overview
This tool does not require login authentication.

This tool downloads texts, pictures (jpg), and videos (mp4) of weibo posts to local PC or Mac.

Please ensure that Google Chrome is installed on your PC or Mac.

As a tool designed to mimic front-end user interactions, in contrast to API-based alternatives that though are more susceptible to media download restrictions, expect a slower speed in data retrieval.

## Introduction
Weibo Downloader is a front-end-based tool specifically designed for downloading Weibo posts and media (texts, pictures and videos). It is created for content download for data analysis and record-keeping. This tool operates without the need for user login and is unaffected by changes to the Weibo API, thanks to its front-end-based approach. However, it is not intended for fast-response scraping, and users should expect slower speeds due to web interactions.

## Features
- No login required for accessing public Weibo posts.
- Unaffected by Weibo API changes due to front-end-based operation.
- Ability to customize characteristic class names for post parsing with `self.dinstict_class_names`.
- Download media content including images and videos.
- Save posts in JSON or CSV formats.
- Configurable for specific date ranges or page limits.

## Installation
```bash
pip install weibo-downloader
```

## Usage
Weibo Downloader can be used in two primary ways:

1. **Use get_weibo_posts_by_name Function Directly**:

    Directly fetch posts for a specific username using the **get_weibo_posts_by_name** function. This method returns a generator to iterate over posts.
    ```python
    from weibo_downloader import get_weibo_posts_by_name
    for post in get_weibo_posts_by_name("your_username", pages=1):
        # process post, such as printing
        print(post)
    ```

2. **Instantiate WeiboDownloader and Run**:

    Create an instance of **WeiboDownloader** with the desired configuration and call the run() method to start fetching posts.

    ```python
    from weibo_downloader import WeiboDownloader
    downloader = WeiboDownloader(username="your_username", pages=1)
    downloader.run()
    ``````

## Input Parameters
- **username**: Weibo username (string).
- **uid**: Weibo user ID (string).
- **save_path_csv**: Path to save posts in CSV format (string).
- **save_path_json**: Path to save posts in JSON format (string).
- **save_media_directory**: Directory to save downloaded media (string).
- **enable_get_video_links**: Enable fetching video links (bool).
- **enable_get_urls**: Enable fetching URLs from the posts (bool).
- **enable_fill_truncated_texts**: Enable filling truncated texts (bool).
- **enable_download_media_all**: Download all media (bool).
- **enable_download_media_image_only**: Download only images (bool).
- **enable_download_media_video_only**: Download only videos (bool).
- **enable_download_media_overwrite**: Overwrite existing media files (bool).
- **enable_simplified_json**: Enable simplified JSON structure (bool).
- **date_from**: Start date for fetching posts (YYYY-MM-DD).
- **date_to**: End date for fetching posts (YYYY-MM-DD).
- **pages**: Number of pages to fetch (int).
- **weibo_timeline_url_prefix**: URL prefix for Weibo timeline (string).

## Customization
Users can customize characteristic class names used for parsing posts through the self.dinstict_class_names attribute, allowing for flexibility in case of changes in the Weibo front-end structure.

## Limitations
Slower speed due to web interactions.
Intended for data analysis and record-keeping, not suited for real-time scraping.
## License
MIT License. See LICENSE for more
information.