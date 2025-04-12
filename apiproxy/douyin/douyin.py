#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re
import requests
import json
import time
import copy
# from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Tuple, Optional
from requests.exceptions import RequestException
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.console import Console

from apiproxy.douyin import douyin_headers
from apiproxy.douyin.urls import Urls
from apiproxy.douyin.result import Result
from apiproxy.douyin.database import DataBase
from apiproxy.common import utils
from utils import logger

# Create global console instance
console = Console()

class Douyin(object):

    def __init__(self, database=False):
        self.urls = Urls()
        self.result = Result()
        self.database = database
        if database:
            self.db = DataBase()
        # Used to set maximum time for repeated requests to an interface
        self.timeout = 10
        self.console = Console()  # Can also create console in instance

    # Extract URL from share link
    def getShareLink(self, string):
        # findall() finds strings matching regex pattern
        return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)[0]

    # Get work ID or user ID
    # Input url supports https://www.iesdouyin.com and https://v.douyin.com
    def getKey(self, url: str) -> Tuple[Optional[str], Optional[str]]:
        """Get resource identifier
        Args:
            url: Douyin share link or web URL
        Returns:
            (resource type, resource ID)
        """
        key = None
        key_type = None

        try:
            r = requests.get(url=url, headers=douyin_headers)
        except Exception as e:
            print('[  Error  ]:Invalid input link!\r')
            return key_type, key

        # Douyin updated image collections to notes
        # Works - first parsed link is share/video/{aweme_id}
        # https://www.iesdouyin.com/share/video/7037827546599263488/?region=CN&mid=6939809470193126152&u_code=j8a5173b&did=MS4wLjABAAAA1DICF9-A9M_CiGqAJZdsnig5TInVeIyPdc2QQdGrq58xUgD2w6BqCHovtqdIDs2i&iid=MS4wLjABAAAAomGWi4n2T0H9Ab9x96cUZoJXaILk4qXOJlJMZFiK6b_aJbuHkjN_f0mBzfy91DX1&with_sec_did=1&titleType=title&schema_type=37&from_ssr=1&utm_source=copy&utm_campaign=client_share&utm_medium=android&app=aweme
        # User - first parsed link is share/user/{sec_uid}
        # https://www.iesdouyin.com/share/user/MS4wLjABAAAA06y3Ctu8QmuefqvUSU7vr0c_ZQnCqB0eaglgkelLTek?did=MS4wLjABAAAA1DICF9-A9M_CiGqAJZdsnig5TInVeIyPdc2QQdGrq58xUgD2w6BqCHovtqdIDs2i&iid=MS4wLjABAAAAomGWi4n2T0H9Ab9x96cUZoJXaILk4qXOJlJMZFiK6b_aJbuHkjN_f0mBzfy91DX1&with_sec_did=1&sec_uid=MS4wLjABAAAA06y3Ctu8QmuefqvUSU7vr0c_ZQnCqB0eaglgkelLTek&from_ssr=1&u_code=j8a5173b&timestamp=1674540164&ecom_share_track_params=%7B%22is_ec_shopping%22%3A%221%22%2C%22secuid%22%3A%22MS4wLjABAAAA-jD2lukp--I21BF8VQsmYUqJDbj3FmU-kGQTHl2y1Cw%22%2C%22enter_from%22%3A%22others_homepage%22%2C%22share_previous_page%22%3A%22others_homepage%22%7D&utm_source=copy&utm_campaign=client_share&utm_medium=android&app=aweme
        # Collection
        # https://www.douyin.com/collection/7093490319085307918
        urlstr = str(r.request.path_url)

        if "/user/" in urlstr:
            # Get user sec_uid
            if '?' in r.request.path_url:
                for one in re.finditer(r'user\/([\d\D]*)([?])', str(r.request.path_url)):
                    key = one.group(1)
            else:
                for one in re.finditer(r'user\/([\d\D]*)', str(r.request.path_url)):
                    key = one.group(1)
            key_type = "user"
        elif "/video/" in urlstr:
            # Get work aweme_id
            key = re.findall('video/(\d+)?', urlstr)[0]
            key_type = "aweme"
        elif "/note/" in urlstr:
            # Get note aweme_id
            key = re.findall('note/(\d+)?', urlstr)[0]
            key_type = "aweme"
        elif "/mix/detail/" in urlstr:
            # Get collection id
            key = re.findall('/mix/detail/(\d+)?', urlstr)[0]
            key_type = "mix"
        elif "/collection/" in urlstr:
            # Get collection id
            key = re.findall('/collection/(\d+)?', urlstr)[0]
            key_type = "mix"
        elif "/music/" in urlstr:
            # Get music id
            key = re.findall('music/(\d+)?', urlstr)[0]
            key_type = "music"
        elif "/webcast/reflow/" in urlstr:
            key1 = re.findall('reflow/(\d+)?', urlstr)[0]
            url = self.urls.LIVE2 + utils.getXbogus(
                f'live_id=1&room_id={key1}&app_id=1128')
            res = requests.get(url, headers=douyin_headers)
            resjson = json.loads(res.text)
            key = resjson['data']['room']['owner']['web_rid']
            key_type = "live"
        elif "live.douyin.com" in r.url:
            key = r.url.replace('https://live.douyin.com/', '')
            key_type = "live"

        if key is None or key_type is None:
            print('[  Error  ]:Invalid input link! Cannot get ID\r')
            return key_type, key

        return key_type, key

    # Temporarily comment out decorator
    # @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def getAwemeInfo(self, aweme_id: str) -> dict:
        """Get work information (with retry mechanism)"""
        retries = 3
        for attempt in range(retries):
            try:
                logger.info(f'[  Info  ]:Requesting work id = {aweme_id}')
                if aweme_id is None:
                    return {}

                start = time.time()  # Start time
                while True:
                    # Interface unstable, sometimes server doesn't return data, need to retry
                    try:
                        # Single work interface returns 'aweme_detail'
                        # Homepage works interface returns 'aweme_list'->['aweme_detail']
                        jx_url = self.urls.POST_DETAIL + utils.getXbogus(
                            f'aweme_id={aweme_id}&device_platform=webapp&aid=6383')

                        raw = requests.get(url=jx_url, headers=douyin_headers).text
                        datadict = json.loads(raw)
                        if datadict is not None and datadict["status_code"] == 0:
                            break
                    except Exception as e:
                        end = time.time()  # End time
                        if end - start > self.timeout:
                            logger.warning(f"Repeated request to interface for {self.timeout}s, still no data")
                            return {}

                # Clear self.awemeDict
                self.result.clearDict(self.result.awemeDict)

                # Default to video
                awemeType = 0
                try:
                    # datadict['aweme_detail']["images"] not None means it's an image collection
                    if datadict['aweme_detail']["images"] is not None:
                        awemeType = 1
                except Exception as e:
                    logger.warning("images not found in interface")

                # Convert to our own format
                self.result.dataConvert(awemeType, self.result.awemeDict, datadict['aweme_detail'])

                return self.result.awemeDict
            except RequestException as e:
                logger.warning(f"Request failed (attempt {attempt+1}/{retries}): {str(e)}")
                time.sleep(2 ** attempt)
            except KeyError as e:
                logger.error(f"Response data format error: {str(e)}")
                break
        return {}

    # Input url supports https://www.iesdouyin.com and https://v.douyin.com
    # mode : post | like mode selection, like for user likes, post for user posts
    def getUserInfo(self, sec_uid, mode="post", count=35, number=0, increase=False, start_time="", end_time=""):
        """Get user information
        Args:
            sec_uid: User ID
            mode: Mode(post:posts/like:likes)
            count: Items per page
            number: Download limit (0 means unlimited)
            increase: Whether to update incrementally
            start_time: Start time, format: YYYY-MM-DD
            end_time: End time, format: YYYY-MM-DD
        """
        if sec_uid is None:
            return None

        # Handle time range
        if end_time == "now":
            end_time = time.strftime("%Y-%m-%d")

        if not start_time:
            start_time = "1970-01-01"
        if not end_time:
            end_time = "2099-12-31"

        self.console.print(f"[cyan]🕒 Time range: {start_time} to {end_time}[/]")

        max_cursor = 0
        awemeList = []
        total_fetched = 0
        filtered_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        ) as progress:
            fetch_task = progress.add_task(
                f"[cyan]📥 Getting {mode} works list...",
                total=None  # Total unknown, use infinite progress bar
            )

            while True:
                try:
                    # Build request URL
                    if mode == "post":
                        url = self.urls.USER_POST + utils.getXbogus(
                            f'sec_user_id={sec_uid}&count={count}&max_cursor={max_cursor}&device_platform=webapp&aid=6383')
                    elif mode == "like":
                        url = self.urls.USER_FAVORITE_A + utils.getXbogus(
                            f'sec_user_id={sec_uid}&count={count}&max_cursor={max_cursor}&device_platform=webapp&aid=6383')
                    else:
                        self.console.print("[red]❌ Invalid mode, only post and like supported[/]")
                        return None

                    # Send request
                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)

                    # Handle response data
                    if not datadict or datadict.get("status_code") != 0:
                        self.console.print(f"[red]❌ API request failed: {datadict.get('status_msg', 'Unknown error')}[/]")
                        break

                    current_count = len(datadict["aweme_list"])
                    total_fetched += current_count

                    # Update progress display
                    progress.update(
                        fetch_task,
                        description=f"[cyan]📥 Retrieved: {total_fetched} works"
                    )

                    # Add time filtering when processing works
                    for aweme in datadict["aweme_list"]:
                        create_time = time.strftime(
                            "%Y-%m-%d",
                            time.localtime(int(aweme.get("create_time", 0)))
                        )

                        # Time filtering
                        if not (start_time <= create_time <= end_time):
                            filtered_count += 1
                            continue

                        # Check number limit
                        if number > 0 and len(awemeList) >= number:
                            self.console.print(f"[green]✅ Reached limit: {number}[/]")
                            return awemeList

                        # Check incremental update
                        if self.database:
                            if mode == "post":
                                if self.db.get_user_post(sec_uid=sec_uid, aweme_id=aweme['aweme_id']):
                                    if increase and aweme['is_top'] == 0:
                                        self.console.print("[green]✅ Incremental update complete[/]")
                                        return awemeList
                                else:
                                    self.db.insert_user_post(sec_uid=sec_uid, aweme_id=aweme['aweme_id'], data=aweme)
                            elif mode == "like":
                                if self.db.get_user_like(sec_uid=sec_uid, aweme_id=aweme['aweme_id']):
                                    if increase and aweme['is_top'] == 0:
                                        self.console.print("[green]✅ Incremental update complete[/]")
                                        return awemeList
                            else:
                                self.console.print("[red]❌ Invalid mode, only post and like supported[/]")
                                return None

                        # Convert data format
                        aweme_data = self._convert_aweme_data(aweme)
                        if aweme_data:
                            awemeList.append(aweme_data)

                    # Check if there's more data
                    if not datadict["has_more"]:
                        self.console.print(f"[green]✅ Retrieved all works: {total_fetched}[/]")
                        break

                    # Update cursor
                    max_cursor = datadict["max_cursor"]

                except Exception as e:
                    self.console.print(f"[red]❌ Error getting works list: {str(e)}[/]")
                    break

        return awemeList

    def _convert_aweme_data(self, aweme):
        """Convert work data format"""
        try:
            self.result.clearDict(self.result.awemeDict)
            aweme_type = 1 if aweme.get("images") else 0
            self.result.dataConvert(aweme_type, self.result.awemeDict, aweme)
            return copy.deepcopy(self.result.awemeDict)
        except Exception as e:
            logger.error(f"Data conversion error: {str(e)}")
            return None

    def getLiveInfo(self, web_rid: str):
        print('[  Info  ]:Requesting live room id = %s\r\n' % web_rid)

        start = time.time()  # Start time
        while True:
            # Interface unstable, sometimes server doesn't return data, need to retry
            try:
                live_api = self.urls.LIVE + utils.getXbogus(
                    f'aid=6383&device_platform=web&web_rid={web_rid}')

                response = requests.get(live_api, headers=douyin_headers)
                live_json = json.loads(response.text)
                if live_json != {} and live_json['status_code'] == 0:
                    break
            except Exception as e:
                end = time.time()  # End time
                if end - start > self.timeout:
                    print("[  Info  ]:Repeated request to interface for " + str(self.timeout) + "s, still no data")
                    return {}

        # Clear dictionary
        self.result.clearDict(self.result.liveDict)

        # Type
        self.result.liveDict["awemeType"] = 2
        # Whether live
        self.result.liveDict["status"] = live_json['data']['data'][0]['status']

        if self.result.liveDict["status"] == 4:
            print('[   📺   ]:Live stream has ended, exiting')
            return self.result.liveDict

        # Live title
        self.result.liveDict["title"] = live_json['data']['data'][0]['title']

        # Live cover
        self.result.liveDict["cover"] = live_json['data']['data'][0]['cover']['url_list'][0]

        # Avatar
        self.result.liveDict["avatar"] = live_json['data']['data'][0]['owner']['avatar_thumb']['url_list'][0].replace(
            "100x100", "1080x1080")

        # Viewer count
        self.result.liveDict["user_count"] = live_json['data']['data'][0]['user_count_str']

        # Nickname
        self.result.liveDict["nickname"] = live_json['data']['data'][0]['owner']['nickname']

        # sec_uid
        self.result.liveDict["sec_uid"] = live_json['data']['data'][0]['owner']['sec_uid']

        # Live room view status
        self.result.liveDict["display_long"] = live_json['data']['data'][0]['room_view_stats']['display_long']

        # Stream
        self.result.liveDict["flv_pull_url"] = live_json['data']['data'][0]['stream_url']['flv_pull_url']

        try:
            # Partition
            self.result.liveDict["partition"] = live_json['data']['partition_road_map']['partition']['title']
            self.result.liveDict["sub_partition"] = \
                live_json['data']['partition_road_map']['sub_partition']['partition']['title']
        except Exception as e:
            self.result.liveDict["partition"] = 'None'
            self.result.liveDict["sub_partition"] = 'None'

        info = '[   💻   ]:Live room: %s  Currently %s  Host: %s Category: %s-%s\r' % (
            self.result.liveDict["title"], self.result.liveDict["display_long"], self.result.liveDict["nickname"],
            self.result.liveDict["partition"], self.result.liveDict["sub_partition"])
        print(info)

        flv = []
        print('[   🎦   ]:Live room quality')
        for i, f in enumerate(self.result.liveDict["flv_pull_url"].keys()):
            print('[   %s   ]: %s' % (i, f))
            flv.append(f)

        rate = int(input('[   🎬   ]Enter number to select stream quality: '))

        self.result.liveDict["flv_pull_url0"] = self.result.liveDict["flv_pull_url"][flv[rate]]

        # Show quality list
        print('[   %s   ]:%s' % (flv[rate], self.result.liveDict["flv_pull_url"][flv[rate]]))
        print('[   📺   ]:Copy link to use download tool')
        return self.result.liveDict

    def getMixInfo(self, mix_id, count=35, number=0, increase=False, sec_uid="", start_time="", end_time=""):
        """Get collection information"""
        if mix_id is None:
            return None

        # Handle time range
        if end_time == "now":
            end_time = time.strftime("%Y-%m-%d")

        if not start_time:
            start_time = "1970-01-01"
        if not end_time:
            end_time = "2099-12-31"

        self.console.print(f"[cyan]🕒 Time range: {start_time} to {end_time}[/]")

        cursor = 0
        awemeList = []
        total_fetched = 0
        filtered_count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=True
        ) as progress:
            fetch_task = progress.add_task(
                "[cyan]📥 Getting collection works...",
                total=None
            )

            while True:  # Outer loop
                try:
                    url = self.urls.USER_MIX + utils.getXbogus(
                        f'mix_id={mix_id}&cursor={cursor}&count={count}&device_platform=webapp&aid=6383')

                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)

                    if not datadict:
                        self.console.print("[red]❌ Failed to get data[/]")
                        break

                    for aweme in datadict["aweme_list"]:
                        create_time = time.strftime(
                            "%Y-%m-%d",
                            time.localtime(int(aweme.get("create_time", 0)))
                        )

                        # Time filtering
                        if not (start_time <= create_time <= end_time):
                            filtered_count += 1
                            continue

                        # Check number limit
                        if number > 0 and len(awemeList) >= number:
                            return awemeList  # Use return instead of break

                        # Check incremental update
                        if self.database:
                            if self.db.get_mix(sec_uid=sec_uid, mix_id=mix_id, aweme_id=aweme['aweme_id']):
                                if increase and aweme['is_top'] == 0:
                                    return awemeList  # Use return instead of break
                            else:
                                self.db.insert_mix(sec_uid=sec_uid, mix_id=mix_id, aweme_id=aweme['aweme_id'], data=aweme)

                        # Convert data
                        aweme_data = self._convert_aweme_data(aweme)
                        if aweme_data:
                            awemeList.append(aweme_data)

                    # Check if there's more data
                    if not datadict.get("has_more"):
                        self.console.print(f"[green]✅ Retrieved all works[/]")
                        break

                    # Update cursor
                    cursor = datadict.get("cursor", 0)
                    total_fetched += len(datadict["aweme_list"])
                    progress.update(fetch_task, description=f"[cyan]📥 Retrieved: {total_fetched} works")

                except Exception as e:
                    self.console.print(f"[red]❌ Error getting works list: {str(e)}[/]")
                    break

        if filtered_count > 0:
            self.console.print(f"[yellow]⚠️  Filtered {filtered_count} works outside time range[/]")

        return awemeList

    def getUserAllMixInfo(self, sec_uid, count=35, number=0):
        print('[  Info  ]:Requesting user id = %s\r\n' % sec_uid)
        if sec_uid is None:
            return None
        if number <= 0:
            numflag = False
        else:
            numflag = True

        cursor = 0
        mixIdNameDict = {}

        print("[  Info  ]:Getting all collection IDs from homepage, please wait...\r")
        print("[  Info  ]:Multiple requests will be made, wait time will be longer...\r\n")
        times = 0
        while True:
            times = times + 1
            print("[  Info  ]:Making request " + str(times) + " for [Collection List]...\r")

            start = time.time()  # Start time
            while True:
                # Interface unstable, sometimes server doesn't return data, need to retry
                try:
                    url = self.urls.USER_MIX_LIST + utils.getXbogus(
                        f'sec_user_id={sec_uid}&count={count}&cursor={cursor}&device_platform=webapp&aid=6383')

                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)
                    print('[  Info  ]:This request returned ' + str(len(datadict["mix_infos"])) + ' items\r')

                    if datadict is not None and datadict["status_code"] == 0:
                        break
                except Exception as e:
                    end = time.time()  # End time
                    if end - start > self.timeout:
                        print("[  Info  ]:Repeated request to interface for " + str(self.timeout) + "s, still no data")
                        return mixIdNameDict


            for mix in datadict["mix_infos"]:
                mixIdNameDict[mix["mix_id"]] = mix["mix_name"]
                if numflag:
                    number -= 1
                    if number == 0:
                        break
            if numflag and number == 0:
                print("\r\n[  Info  ]:[Collection List] specified number of collections retrieved...\r\n")
                break

            # Update cursor
            cursor = datadict["cursor"]

            # Exit condition
            if datadict["has_more"] == 0 or datadict["has_more"] == False:
                print("[  Info  ]:[Collection List] all collection IDs retrieved...\r\n")
                break
            else:
                print("\r\n[  Info  ]:[Collection List] request " + str(times) + " successful...\r\n")

        return mixIdNameDict

    def getMusicInfo(self, music_id: str, count=35, number=0, increase=False):
        print('[  Info  ]:Requesting music collection id = %s\r\n' % music_id)
        if music_id is None:
            return None
        if number <= 0:
            numflag = False
        else:
            numflag = True

        cursor = 0
        awemeList = []
        increaseflag = False
        numberis0 = False

        print("[  Info  ]:Getting all works from music collection, please wait...\r")
        print("[  Info  ]:Multiple requests will be made, wait time will be longer...\r\n")
        times = 0
        while True:
            times = times + 1
            print("[  Info  ]:Making request " + str(times) + " for [Music Collection]...\r")

            start = time.time()  # Start time
            while True:
                # Interface unstable, sometimes server doesn't return data, need to retry
                try:
                    url = self.urls.MUSIC + utils.getXbogus(
                        f'music_id={music_id}&cursor={cursor}&count={count}&device_platform=webapp&aid=6383')

                    res = requests.get(url=url, headers=douyin_headers)
                    datadict = json.loads(res.text)
                    print('[  Info  ]:This request returned ' + str(len(datadict["aweme_list"])) + ' items\r')

                    if datadict is not None and datadict["status_code"] == 0:
                        break
                except Exception as e:
                    end = time.time()  # End time
                    if end - start > self.timeout:
                        print("[  Info  ]:Repeated request to interface for " + str(self.timeout) + "s, still no data")
                        return awemeList


            for aweme in datadict["aweme_list"]:
                if self.database:
                    # Exit conditions
                    if increase is False and numflag and numberis0:
                        break
                    if increase and numflag and numberis0 and increaseflag:
                        break
                    # Incremental update, find latest non-pinned work publish time
                    if self.db.get_music(music_id=music_id, aweme_id=aweme['aweme_id']) is not None:
                        if increase and aweme['is_top'] == 0:
                            increaseflag = True
                    else:
                        self.db.insert_music(music_id=music_id, aweme_id=aweme['aweme_id'], data=aweme)

                    # Exit conditions
                    if increase and numflag is False and increaseflag:
                        break
                    if increase and numflag and numberis0 and increaseflag:
                        break
                else:
                    if numflag and numberis0:
                        break

                if numflag:
                    number -= 1
                    if number == 0:
                        numberis0 = True

                # Clear self.awemeDict
                self.result.clearDict(self.result.awemeDict)

                # Default to video
                awemeType = 0
                try:
                    if aweme["images"] is not None:
                        awemeType = 1
                except Exception as e:
                    print("[  Warning  ]:images not found in interface\r")

                # Convert to our own format
                self.result.dataConvert(awemeType, self.result.awemeDict, aweme)

                if self.result.awemeDict is not None and self.result.awemeDict != {}:
                    awemeList.append(copy.deepcopy(self.result.awemeDict))

            if self.database:
                if increase and numflag is False and increaseflag:
                    print("\r\n[  Info  ]:[Music Collection] works incremental update complete...\r\n")
                    break
                elif increase is False and numflag and numberis0:
                    print("\r\n[  Info  ]:[Music Collection] specified number of works retrieved...\r\n")
                    print("\r\n[  Info  ]: [Music Collection] specified number of works retrieved...\r\n")
                    break
                elif increase and numflag and numberis0 and increaseflag:
                    print("\r\n[  Info  ]: [Music Collection] specified number of works retrieved, incremental update complete...\r\n")
                    break
            else:
                if numflag and numberis0:
                    print("\r\n[  Info  ]: [Music Collection] specified number of works retrieved...\r\n")
                    break

            # Update cursor
            cursor = datadict["cursor"]

            # Exit conditions
            if datadict["has_more"] == 0 or datadict["has_more"] == False:
                print("\r\n[  Info  ]:[Music Collection] all works data retrieved...\r\n")
                break
            else:
                print("\r\n[  Info  ]:[Music Collection] request " + str(times) + " successful...\r\n")

        return awemeList

    def getUserDetailInfo(self, sec_uid):
        if sec_uid is None:
            return None

        datadict = {}
        start = time.time()  # Start time
        while True:
            # Interface unstable, sometimes server doesn't return data, need to retry
            try:
                url = self.urls.USER_DETAIL + utils.getXbogus(
                        f'sec_user_id={sec_uid}&device_platform=webapp&aid=6383')

                res = requests.get(url=url, headers=douyin_headers)
                datadict = json.loads(res.text)

                if datadict is not None and datadict["status_code"] == 0:
                    return datadict
            except Exception as e:
                end = time.time()  # End time
                if end - start > self.timeout:
                    print("[  Info  ]:Repeated requests to interface for " + str(self.timeout) + "s, still no data received")
                    return datadict


if __name__ == "__main__":
    pass
