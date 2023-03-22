import requests
import os
import json
import re
import logging
import cv2 as cv
import numpy as np
from datetime import date
from ast import literal_eval
from base64 import b64encode
from onepush import notify
from .config import config, history, project_path
from random import randrange
from time import sleep

def today():
    return date.today()

log = logging.getLogger(__name__)
log_path = os.path.join(project_path, 'logs')
try:
    log_list = os.listdir(log_path)
except FileNotFoundError:
    os.mkdir(log_path)
    log_list = os.listdir(log_path)
file_num = len(log_list)
if file_num > 7:
    for i in range(file_num - 7):
        os.remove(os.path.join(log_path,log_list[i]))
log_file = os.path.join(log_path, f"log_{today().strftime('%Y%m%d')}.log")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S',filename=log_file,encoding='UTF-8')

console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
console_handler.setFormatter(formatter)
log.addHandler(console_handler)

class SignException(Exception):
    """Base exception."""

    def __init__(self, message):
        super().__init__(message)
        log.error(message)

INFECTION_STATE = ["was","on-going","never"]

CN_NUM = {
    '一': '1', '二': '2', '三': '3', '四': ' 4', '五': '5', '六': '6', '七': '7', '八': '8', '九': '9', '零': '0',
    '壹': '1', '贰': '2', '叁': '3', '肆': '4', '伍': '5', '陆': '6', '柒': '7', '捌': '8', '玖': '9', '貮': '2'
}

zzu_geo_dict = {
    'myvs_13a': '41',
    'myvs_13b': '4151',
    'myvs_13c': '河南省郑州市郑州大学主校区',
    'jingdu': '113.539800',
    'weidu': '34.826700'
}


class API_Baidu:
    def __init__(self) -> None:
        self.AK = config.ak_for_baidu_map #百度地图开放平台AK
        if not config.is_expired:
            access_token = config.ocr_access_token
        else:
            log.info('Access token expired ...')
            access_token = self.acquire_access_token()
        self.handwriting_url = f'https://aip.baidubce.com/rest/2.0/ocr/v1/handwriting?access_token={access_token}'
        self.basic_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic?access_token={access_token}"
        self.webimg_url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/webimage?access_token={access_token}"
        
    
    def geocoding(self, address: str):
        api = f'https://api.map.baidu.com/geocoding/v3/?address={address}&output=json&ak={self.AK}&callback=showLocation'
        res = requests.get(api)
        results = json.loads(re.findall(r'\((.*?)\)', res.text)[0])
        if results['status'] == 0:
            longitude = results['result']['location']['lng']
            latitude = results['result']['location']['lat']
            return longitude, latitude
        else:
            log.debug(res.text)

    def reverse_geocoding(self, lng: float, lat: float):
        api = f'https://api.map.baidu.com/reverse_geocoding/v3/?ak={self.AK}&output=json&coordtype=wgs84ll&location={lat},{lng}'
        res = requests.get(api)
        res = json.loads(res.text)
        if res['status'] == 0:
            adcode = res['result']['addressComponent']['adcode']
            return str(adcode)
        else:
            log.debug(res)

    def ocr(self, img_path: str = None, img_url: str = None, metadata: bytes = None) -> str:
        '''
        封装有百度通用文字识别（高精度版）和手写识别的api，返回一串4位的数字验证码。
        >>> img_path:验证码的本地路径
        >>> img_url:验证码的url
        >>> metadata:将图片二进制打开后，用base64编码后的数据
        优先级顺序为img_path、metadata、img_url，当img_path存在时，metadata和img_url失效。
        '''
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        params = {
            "image": read_img(img_path) if img_path else metadata,
            "url": img_url
        }
        for i in range(4):
            log.info(f'第{i+1}次尝试 ...')
            response = requests.post(self.basic_url if i % 2 == 0 else self.handwriting_url, data=params, headers=headers).json()
            try:
                if not response['words_result_num']:
                    continue
                code = translate(response)
                if check_code(code) or i == 3:
                    return code
            except:
                log.info(response)

    def ocr_stable(self, img_path:str = None, img_url:str = None) -> str:
        '''
        Try to identify the verification code in the whole image.
        If it fails to get a valid code, then split the image into Four images, identify them individually.
        img_path has a higher priority than img_url.
        '''
        code = self.ocr(img_path=img_path, img_url=img_url)
        if len(code) == 4:
            log.info(f'Verification code is {code}')
            return code
        code = ''
        image = cv_read(img_path=img_path, img_url=img_url)
        height = int(image.shape[0])
        quarter = int(image.shape[1]/4)
        img_data_list = [image[0:height, i*quarter : (i+1)*quarter] for i in range(4)]
        for img in img_data_list:
            img_encode = b64encode(cv.imencode('.png', img)[1].tobytes())
            code = code + self.ocr(metadata=img_encode)
        log.info(f'Verification code is {code}')
        return code

    def acquire_access_token(self) -> str:
        #client_id 为官网获取的AK，client_secret 为官网获取的SK
        host = f'https://aip.baidubce.com/oauth/2.0/token'
        data = {
            'grant_type': 'client_credentials',
            'client_id': config.ocr_ak,
            'client_secret': config.ocr_sk
        }
        log.info('Acquiring new access token ...')
        response = requests.get(host,params=data).json()
        config.ocr_access_token = response['access_token'] if response else 'token获取失败'
        try:
            config.save_token()
        except:
            log.error('Writing access token failed ...')
        return config.ocr_access_token


class Delay:
    def __init__(self) -> None:
        pass
    
    def sleep(self, sleep_time: int):
        for i in range(sleep_time):
            print("Sleep for {} seconds ...".format(sleep_time - 1 - i), end='\r')
            sleep(1)
        
    def random_delay(self):
        interval = randrange(1, 30)
        return self.sleep(interval)

    def custom_random_delay(self, sleep_interval: str = None):
        start, end = sleep_interval.split('-')
        interval = randrange(int(start), int(end))
        return self.sleep(interval)

    def custom_delay(self, sleeptime):
        return self.sleep(sleeptime)

    @staticmethod
    def pause_then_exit():
        for i in range(10):
            print(" This program will automatically shut down in {} seconds ...".format(9 - i), end='\r')
            sleep(1)

api_baidu = API_Baidu()
delay = Delay()

def translate(response: dict) -> str:
    '''
    Process the dict returned from Baidu ocr api.
    Return a string that only contains Arabic numbers.
    If there are Chinese numbers in words result, then translate them into Arabic numbers.
    >>> response: response from Baidu ocr api
    '''
    result = ''
    try:
        for i in response['words_result']:
            result = result + i['words']
    except:
        log.error('Invalid response ...')
        return
    log.info(f"Ocr result is {result} ...")
    new_str = re.sub("[^\u4e00-\u9fa50-9]", '', result)
    result = ''
    for i in new_str:
        try:
            result = result + CN_NUM.get(i)
        except:
            result = result + i
    return re.sub("[^0-9]", '', result)

def cv_read(img_url:str = None, img_path:str = None):
    '''
    从url或本地中获取图片，返回opencv读取后的图片。
    img_path优先级高于img_url
    '''
    if img_path:
        return cv.imread(img_path)
    header = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0'
        }
    file = requests.get(img_url,headers=header)
    return cv.imdecode(np.frombuffer(file.content, np.uint8), 1)

def read_img(img_file) -> bytes:
    '''
    Read an image a from local file and return the data encoded with base64.
    '''
    try:
        with open(img_file,'rb') as f:
            return b64encode(f.read())
    except Exception:
        raise Exception
        
def check_code(code) -> bool:
    '''
    Make sure the verification code is valid.
    '''
    return True if len(code) in [1,4] else False

def str_to_dict(str: str) -> dict:
    return literal_eval(str.lower().replace('null', 'None') if 'null' in str.lower() else str)

def process_msg(msg: dict) -> str:
    msg_all = ''
    for i, o in msg.items():
        log = f"您于{o['date']} {o['msg']}"
        msg_all = (msg_all if not msg_all else f'{msg_all}\n') + log
    return msg_all

def notify_user(user, title, content) -> dict:
    config.get_config(user)
    notifier = config.notifier
    key = config.key
    if not notifier or not key:
        log.info('No notification method configured ...')
        return
    log.info('Preparing to send notification ...')
    return str_to_dict(notify(notifier, key=key, title=title, content=content, group='zzuSign').text)

MSG_TEMPLATE = '''本周健康打卡情况如下：
  {detailed_msg}''' 
MSG_EXAMPLE = '''{date} {msg}\n'''

def format_msg(user):
    msg_list = []
    for k,v in history.get_history(user).items():
        msg_list.append(MSG_EXAMPLE.format(**v))
    return MSG_TEMPLATE.format(detailed_msg = '  '.join(msg_list))

def regularly_notify():
    if history.what_day == config.notify_day:
        notify_list = config.active_users
        for count in range(5):
            for user in notify_list.copy():
                response = notify_user(user, "健康打卡例行通知", format_msg(user))
                retcode = response['code']
                if retcode == 200:
                    log.info(f'Message delivered to {config.name.title()} ...')
                    notify_list.remove(user)
            if not len(notify_list):
                log.info("Notification delivery completed ...")
                break
            elif count == 4:
                msg = f"{notify_list} didn't get notified ..."
                log.error(msg)
                notify_user('user0', "有没完成的通知推送", msg)
                break
            elif count > 0 and count < 4:
                delay.custom_random_delay(60, 120)
    else:
        log.info('未满足推送条件 ...')
        return
