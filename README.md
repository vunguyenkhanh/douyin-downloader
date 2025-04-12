# DouYin Downloader

DouYin Downloader is a tool designed for bulk downloading content from Douyin. It is built on the Douyin API and supports both command-line arguments and YAML configuration files, meeting most content downloading needs from the platform.

## ✨ Features

- **Support for Multiple Content Types**
  - Download of videos, photo albums, music, and livestream information
  - Supports various types of links, including personal profiles, shared posts, livestreams, collections, and music playlists
  - Supports watermark-free downloads
  
- **Bulk download capability**
  - Multi-threaded concurrent downloading
  - Supports batch downloading from multiple links
  - Automatically skips already downloaded content
  
- **Flexible configuration**
  - Supports both command-line arguments and configuration file modes
  - Customizable download path, number of threads, and more
  - Supports download quantity limits
  
- **Incremental updates**
  - Supports incremental updates for content on personal profiles
  - Supports data persistence to a database
  - Supports filtering by time range

## 🚀 Quick Start

### Installation

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Copy the configuration file:
```bash
cp config.example.yml config.yml
```

### Configuration

Edit the `config.yml` file to set:
- Download link
- Save path
- Cookie information (retrieved from the browser’s developer tools)
- Other download options

### Run 

**Method 1: Using a configuration file (recommended)**
```bash
python DouYinCommand.py
```

**Method 2: Using the command line**
```bash
python DouYinCommand.py -C True -l "Douyin share link" -p "Download path"
```

## User support group

![fuye](img/fuye.png)

## Usage screenshots

![DouYinCommand1](img/DouYinCommand1.png)
![DouYinCommand2](img/DouYinCommand2.png)
![DouYinCommand download](img/DouYinCommanddownload.jpg)
![DouYinCommand download detail](img/DouYinCommanddownloaddetail.jpg)

## 📝 Supported link types

- Post share link：`https://v.douyin.com/xxx/`
- Personal profile：`https://www.douyin.com/user/xxx`
- Single video：`https://www.douyin.com/video/xxx`
- Photo album：`https://www.douyin.com/note/xxx`
- Collection：`https://www.douyin.com/collection/xxx`
- Original music：`https://www.douyin.com/music/xxx`
- Livestream：`https://live.douyin.com/xxx`

## 🛠️ Advanced Usage

### Command-line arguments

Basic parameters：
```
-C, --cmd           Use command-line mode
-l, --link          Download link
-p, --path          Save path
-t, --thread        Number of threads (default: 5)
```

下载选项：
```
-m, --music         Download music (default: True)
-c, --cover         Download cover image (default: True)
-a, --avatar        Download avatar (default: True)
-j, --json          Save JSON data (default: True)
```

For more parameter details, use `-h` to view the help information.

### Example command

1. Download a single video:
```bash
python DouYinCommand.py -C True -l "https://v.douyin.com/xxx/"
```

2. Download posts from a personal profile:
```bash
python DouYinCommand.py -C True -l "https://v.douyin.com/xxx/" -M post
```

3. Batch download:
```bash
  python DouYinCommand.py -C True -l "Link 1" -l "Link 2" -p "./downloads"
```

For more examples, please refer to[Usage example documentation](docs/examples.md)。

## 📋 Important Notes

1. This project is for learning and educational purposes only.
2. Please ensure all required dependencies are installed before use.
3. Cookie information must be obtained manually.
4. It is recommended to adjust the number of threads appropriately to avoid sending requests too frequently.

## 🤝 Contributing

Feel free to submit Issues and Pull Requests.

## 📜 License

This project is licensed under the [MIT](LICENSE) License。

## 🙏 Acknowledgments

- [TikTokDownload](https://github.com/Johnserf-Seed/TikTokDownload)
- This project was developed with the assistance of ChatGPT. If you encounter any issues, please submit an Issue.

## 📊 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=jiji262/douyin-downloader&type=Date)](https://star-history.com/#jiji262/douyin-downloader&Date)




# License

[MIT](https://opensource.org/licenses/MIT) 

