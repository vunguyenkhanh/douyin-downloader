# Usage Examples

This document provides detailed usage examples of the Douyin downloader to help you better use the tool.

## 1. Configuration File Method

### Basic Configuration

Create `config.yml` file:

```yaml
# Download Links
link:
  - 'https://v.douyin.com/xxxxx/' # Post link
  - 'https://www.douyin.com/user/xxxxx' # User homepage

# Save Path
path: './downloads'

# Download Options
music: true # Download music
cover: true # Download cover
avatar: true # Download avatar
json: true # Save JSON data
```

Run command:

```bash
python DouYinCommand.py
```

### Time Range Filtering

```yaml
# Only download works within specified time range
start_time: "2023-01-01"  # Start time
end_time: "2023-12-31"    # End time
# Or use "now" to represent current time
end_time: "now"
```

### 增量更新

```yaml
increase:
  post: true # Incremental update of published works
  like: false # Do not incrementally update liked works
  mix: true # Incremental update of collections
```

### 数量限制

```yaml
number:
  post: 10 # Only download the latest 10 published works
  like: 5 # Only download the latest 5 liked works
  mix: 3 # Only download the latest 3 collection works
```

## 2. Command Line Usage

### Download Single Video

```bash
python DouYinCommand.py -C True -l "https://v.douyin.com/xxxxx/"
```

### Download User Profile Works

```bash
# Download published works
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M post

# Download liked works
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M like

# Download both published and liked works
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M post -M like
```

### Download Collections

```bash
# Download single collection
python DouYinCommand.py -C True -l "https://www.douyin.com/collection/xxxxx"

# Download all user collections
python DouYinCommand.py -C True -l "https://www.douyin.com/user/xxxxx" -M mix
```

### Custom Save Options

```bash
# Do not download music and cover
python DouYinCommand.py -C True -l "Link" -m False -c False

# Custom save path
python DouYinCommand.py -C True -l "Link" -p "./my_downloads"
```

### Batch Download

```bash
# Download multiple links
python DouYinCommand.py -C True -l "Link 1" -l "Link 2" -l "Link 3"

# Use multiple threads
python DouYinCommand.py -C True -l "Link" -t 10
```

## 3. Advanced Usage

### Cookie Settings

If you encounter access restrictions, you can set Cookie:

Configuration file method:

```yaml
cookies:
  msToken: 'xxx'
  ttwid: 'xxx'
  odin_tt: 'xxx'
```

Command line method:

```bash
python DouYinCommand.py -C True -l "Link" --cookie "msToken=xxx; ttwid=xxx;"
```

### Database Support

Enable database to support incremental updates:

```yaml
database: true
```

### Folder Style

Control file saving structure:

```yaml
folderstyle: true # Create separate folder for each work
```

## 4. Common Issues

1. **Download Failed**

   - Check network connection
   - Update Cookie
   - Reduce concurrent threads

2. **Link Not Found**

   - Ensure correct link format
   - Use latest share link

3. **Incremental Update Not Working**
   - Ensure database is enabled
   - Check database permissions

## 5. Best Practices

1. Use configuration files to manage complex download tasks
2. Set appropriate thread count (recommended 5-10)
3. Update Cookie regularly
4. Use time range filtering to avoid downloading too much content
5. Enable database support for incremental updates

For more help, please submit an Issue.

## Error Handling Examples

### 1. Network Error Handling

```python
try:
    downloader.download_with_resume(url, filepath, "Video Download")
except requests.exceptions.ConnectionError:
    logger.error("Network connection failed")
except requests.exceptions.Timeout:
    logger.error("Download timeout")
```

### 2. File System Error Handling

```python
try:
    with open(filepath, 'wb') as f:
        # Download code...
except PermissionError:
    logger.error("Permission denied")
except OSError as e:
    logger.error(f"File system error: {e}")
```
