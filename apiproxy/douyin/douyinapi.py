#!/usr/bin/env python
# -*- coding: utf-8 -*-


import re
import requests
import json
import time
import copy

from apiproxy.douyin import douyin_headers
from apiproxy.douyin.urls import Urls
from apiproxy.douyin.result import Result
from apiproxy.common import utils

class DouyinApi(object):
    def __init__(self):
        self.urls = Urls()
        self.result = Result()
        # Used to set the maximum time to repeatedly request an interface
        self.timeout = 10

    # Extract URL from share link
    def getShareLink(self, string):
        # findall() finds strings matching the regular expression
        return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', string)[0]

    # Get work ID or user ID
    # Input URL supports https://www.iesdouyin.com and https://v.douyin.com
    def getKey(self, url):
        key = None
        key_type = None

        try:
            r = requests.get(url=url, headers=douyin_headers)
        except Exception as e:
            print('[  Error  ]: Invalid input link!\r')
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
            print('[  Error  ]: Invalid input link! Unable to get ID\r')
            return key_type, key

        return key_type, key

    def getAwemeInfoApi(self, aweme_id):
        if aweme_id is None:
            return None
        start = time.time()  # Start time
        while True:
            try:
                jx_url = self.urls.POST_DETAIL + utils.getXbogus(
                    f'aweme_id={aweme_id}&device_platform=webapp&aid=6383')

                raw = requests.get(url=jx_url, headers=douyin_headers).text
                datadict = json.loads(raw)
                if datadict is not None and datadict["status_code"] == 0:
                    break
            except Exception as e:
                end = time.time()  # End time
                if end - start > self.timeout:
                    return None

        # Clear self.awemeDict
        self.result.clearDict(self.result.awemeDict)

        # Default is video
        awemeType = 0
        try:
            if datadict['aweme_detail']["images"] is not None:
                awemeType = 1
        except Exception as e:
            pass

        # Convert to our own format
        self.result.dataConvert(awemeType, self.result.awemeDict, datadict['aweme_detail'])

        return self.result.awemeDict, datadict

    def getUserInfoApi(self, sec_uid, mode="post", count=35, max_cursor=0):
        if sec_uid is None:
            return None

        awemeList = []

        start = time.time()  # Start time
        while True:
            try:
                if mode == "post":
                    url = self.urls.USER_POST + utils.getXbogus(
                        f'sec_user_id={sec_uid}&count={count}&max_cursor={max_cursor}&device_platform=webapp&aid=6383')
                elif mode == "like":
                    url = self.urls.USER_FAVORITE_A + utils.getXbogus(
                        f'sec_user_id={sec_uid}&count={count}&max_cursor={max_cursor}&device_platform=webapp&aid=6383')
                else:
                    return None

                res = requests.get(url=url, headers=douyin_headers)
                datadict = json.loads(res.text)
                if datadict is not None and datadict["status_code"] == 0:
                    break
            except Exception as e:
                end = time.time()  # End time
                if end - start > self.timeout:
                    return None

        for aweme in datadict["aweme_list"]:
            # Clear self.awemeDict
            self.result.clearDict(self.result.awemeDict)

            # Default is video
            awemeType = 0
            try:
                if aweme["images"] is not None:
                    awemeType = 1
            except Exception as e:
                pass

            # Convert to our own format
            self.result.dataConvert(awemeType, self.result.awemeDict, aweme)

            if self.result.awemeDict is not None and self.result.awemeDict != {}:
                awemeList.append(copy.deepcopy(self.result.awemeDict))

        return awemeList, datadict, datadict["max_cursor"], datadict["has_more"]

    def getLiveInfoApi(self, web_rid: str):
        start = time.time()  # Start time
        while True:
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
                    return None

        # Clear dictionary
        self.result.clearDict(self.result.liveDict)

        # Type
        self.result.liveDict["awemeType"] = 2
        # Is streaming
        self.result.liveDict["status"] = live_json['data']['data'][0]['status']

        if self.result.liveDict["status"] == 4:
            return self.result.liveDict, live_json

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

        # Live room viewing status
        self.result.liveDict["display_long"] = live_json['data']['data'][0]['room_view_stats']['display_long']

        # Stream URL
        self.result.liveDict["flv_pull_url"] = live_json['data']['data'][0]['stream_url']['flv_pull_url']

        try:
            # Category
            self.result.liveDict["partition"] = live_json['data']['partition_road_map']['partition']['title']
            self.result.liveDict["sub_partition"] = \
                live_json['data']['partition_road_map']['sub_partition']['partition']['title']
        except Exception as e:
            self.result.liveDict["partition"] = 'None'
            self.result.liveDict["sub_partition"] = 'None'

        flv = []

        for i, f in enumerate(self.result.liveDict["flv_pull_url"].keys()):
            flv.append(f)

        self.result.liveDict["flv_pull_url0"] = self.result.liveDict["flv_pull_url"][flv[0]]

        return self.result.liveDict, live_json

    def getMixInfoApi(self, mix_id: str, count=35, cursor=0):
        if mix_id is None:
            return None

        awemeList = []

        start = time.time()  # Start time
        while True:
            try:
                url = self.urls.USER_MIX + utils.getXbogus(
                    f'mix_id={mix_id}&cursor={cursor}&count={count}&device_platform=webapp&aid=6383')

                res = requests.get(url=url, headers=douyin_headers)
                datadict = json.loads(res.text)
                if datadict is not None:
                    break
            except Exception as e:
                end = time.time()  # End time
                if end - start > self.timeout:
                    return None

        for aweme in datadict["aweme_list"]:

            # Clear self.awemeDict
            self.result.clearDict(self.result.awemeDict)

            # Default is video
            awemeType = 0
            try:
                if aweme["images"] is not None:
                    awemeType = 1
            except Exception as e:
                pass

            # Convert to our own format
            self.result.dataConvert(awemeType, self.result.awemeDict, aweme)

            if self.result.awemeDict is not None and self.result.awemeDict != {}:
                awemeList.append(copy.deepcopy(self.result.awemeDict))

        return awemeList, datadict, datadict["cursor"], datadict["has_more"]

    def getUserAllMixInfoApi(self, sec_uid, count=35, cursor=0):

        if sec_uid is None:
            return None

        mixIdlist = []

        start = time.time()  # Start time
        while True:
            try:
                url = self.urls.USER_MIX_LIST + utils.getXbogus(
                    f'sec_user_id={sec_uid}&count={count}&cursor={cursor}&device_platform=webapp&aid=6383')

                res = requests.get(url=url, headers=douyin_headers)
                datadict = json.loads(res.text)
                if datadict is not None and datadict["status_code"] == 0:
                    break
            except Exception as e:
                end = time.time()  # End time
                if end - start > self.timeout:
                    return None

        for mix in datadict["mix_infos"]:
            mixIdNameDict = {}
            mixIdNameDict["https://www.douyin.com/collection/" + mix["mix_id"]] = mix["mix_name"]
            mixIdlist.append(mixIdNameDict)

        return mixIdlist, datadict, datadict["cursor"], datadict["has_more"]

    def getMusicInfoApi(self, music_id: str, count=35, cursor=0):
        if music_id is None:
            return None

        awemeList = []

        start = time.time()  # Start time
        while True:
            try:
                url = self.urls.MUSIC + utils.getXbogus(
                    f'music_id={music_id}&cursor={cursor}&count={count}&device_platform=webapp&aid=6383')

                res = requests.get(url=url, headers=douyin_headers)
                datadict = json.loads(res.text)
                if datadict is not None and datadict["status_code"] == 0:
                    break
            except Exception as e:
                end = time.time()  # End time
                if end - start > self.timeout:
                    return None

        for aweme in datadict["aweme_list"]:
            # Clear self.awemeDict
            self.result.clearDict(self.result.awemeDict)

            # Default is video
            awemeType = 0
            try:
                if aweme["images"] is not None:
                    awemeType = 1
            except Exception as e:
                pass

            # Convert to our own format
            self.result.dataConvert(awemeType, self.result.awemeDict, aweme)

            if self.result.awemeDict is not None and self.result.awemeDict != {}:
                awemeList.append(copy.deepcopy(self.result.awemeDict))

        return awemeList, datadict, datadict["cursor"], datadict["has_more"]

    def getUserDetailInfoApi(self, sec_uid):
        if sec_uid is None:
            return None

        start = time.time()  # Start time
        while True:
            # Interface is unstable, sometimes server doesn't return data, need to retry
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
                    return None



if __name__ == "__main__":
    pass
