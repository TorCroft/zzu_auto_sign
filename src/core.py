import re
import requests
from bs4 import BeautifulSoup
from .utils import api_baidu, log, zzu_geo_dict, INFECTION_STATE, SignException


class sign_core(object):
    def __init__(self, name, id, pwd, addr, infection_state) -> None:
        self.name = name
        self.id = str(id)
        self.pwd = str(pwd)
        self.address = addr
        self.infection_stat = infection_state if infection_state else "never"
        self.message = None

        self.text = ''
        self.bs4 = None
        self.ptopid = None
        self.sid = None
        self.fun18 = None

        self.login_url = "https://jksb.v.zzu.edu.cn/vls6sss/zzujksb.dll/login"
        self.checkstatus_url = "https://jksb.v.zzu.edu.cn/vls6sss/zzujksb.dll/jksb?ptopid={}&sid={}&fun2="
        self.submit_url = "https://jksb.v.zzu.edu.cn/vls6sss/zzujksb.dll/jksb"

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0',
            'referer': 'https://jksb.v.zzu.edu.cn/vls6sss/zzujksb.dll/first0?fun2=a',
            "Content-Type": 'application/x-www-form-urlencoded'
        }
        self.form = {}
        self.form_final = {}

    def login(self) -> bool:
        log.info("Logging in ...")
        self.form = {
            "uid": self.id,
            "upw": self.pwd,
            "smbtn": "进入健康状况上报平台",
            "hh28": "750"
        }
        for i in range(3):
            try:
                r = requests.post(self.login_url, headers=self.headers, data=self.form, timeout=(200, 200))
            except:
                if i == 2:
                    raise SignException('Please check your Internet connection ...')
            else:
                self.text = r.text.encode(r.encoding).decode(r.apparent_encoding)
                matchObj = re.search(r'ptopid=(\w+)\&sid=(\w+)\"', self.text)
                break
        try:
            self.ptopid = matchObj.group(1)
            self.sid = matchObj.group(2)
        except:
            if '密码输入错误' in self.text:
                self.message = 'Wrong password ...'
            elif '未检索到用户账号' in self.text:
                self.message = "Account doesn't exist ..."
            elif '验证码' in self.text:
                self.message = "Verification code is required ..."
            else:
                self.message = "Unknown reason ..."
            log.error(self.message)
            return False
        else:
            log.info("Successfully logged in ...")
            return True

    def checkstatus(self) -> bool:
        try:
            r = requests.get(self.checkstatus_url.format(self.ptopid, self.sid))
            self.text = r.text.encode(r.encoding).decode(r.apparent_encoding)
            self.bs4 = BeautifulSoup(self.text, 'html.parser')
            self.name = self.bs4.find('span', attrs={'style': "color:#016d77"}).find_next('span').text
        except Exception:
            log.error('获取姓名失败 ...')
        msg = self.bs4.find('span')
        if ("今日您已经填报过了" in msg):
            return True
        else:
            return False


    def prepare_form(self):
        self.ptopid = self.bs4.find(name='input', attrs={'name': 'ptopid'}).get('value')
        self.sid = self.bs4.find(name='input', attrs={'name': 'sid'}).get('value')
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0',
            'referer': self.login_url
        }
        try:
            # response为jksb表单第一页
            r = requests.get(self.checkstatus_url.format(self.ptopid, self.sid), headers=self.headers)
        except:
            log.error("未能获取表单第一页 ...")

        self.text = r.text.encode(r.encoding).decode(r.apparent_encoding)
        matchObj = re.search(r'name=\"ptopid\" value=\"(\w+)\".+name=\"sid\" value=\"(\w+)\".+', self.text)
        self.ptopid = matchObj.group(1)
        self.sid = matchObj.group(2)
        self.form = {
            "day6": "b",
            "did": "1",
            "door": "",
            "men6": "a",
            "ptopid": self.ptopid,
            "sid": self.sid
        }

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0',
            'Referer': f'https://jksb.v.zzu.edu.cn/vls6sss/zzujksb.dll/jksb?ptopid={self.ptopid}&sid={self.sid}&fun2=',
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        try:
            r = requests.post(self.submit_url, headers=self.headers, data=self.form)  # response为打卡的第二个表单
        except Exception as e:
            log.info(e)
        self.text = r.text.encode(r.encoding).decode(r.apparent_encoding)
        self.bs4 = BeautifulSoup(self.text, 'html.parser')
        try:
            code_url = self.bs4.find('img').get('src') if '验证码' in self.text else None
        except:
            code_url = None
            log.info('未能找到验证码url')
        data = self.bs4.find('form', attrs={'name': 'myform52'}).find_all('input')
        infection_option = self.bs4.find('form', attrs={'name': 'myform52'}).find_all('option')
        try:
            v = infection_option[INFECTION_STATE.index(self.infection_stat)].get('value')
        except:
            v = infection_option[-1].get('value')
        for i in data:
            self.form_final[i.get('name')] = i.get('value')
        form_middle = {
            self.bs4.find('form', attrs={'name': 'myform52'}).find('select').get('name'): v,
            "myvs_94c": api_baidu.ocr_stable(img_url=code_url) if code_url else None,
            "ptopid": self.bs4.find('input',attrs={'name':"ptopid"}).get('value'),
            "sid": self.bs4.find('input',attrs={'name':"sid"}).get('value')
        }
        self.form_final.update(form_middle)
        self.form_final.update(self.addr_form)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:98.0) Gecko/20100101 Firefox/98.0',
            'Referer': self.submit_url,
            'Content-Type': 'application/x-www-form-urlencoded'
        }

    @property
    def addr_form(self) -> dict[str,str]:
        if self.address:
            lng, lat = api_baidu.geocoding(self.address)
            adcode = api_baidu.reverse_geocoding(lng, lat)
            return {
                "myvs_13a": adcode[0:2],
                "myvs_13b": adcode[0:4],
                "myvs_13c": self.address,
                "jingdu": str(round(lng, 6)),
                "weidu": str(round(lat, 6))
            }
        else:
            try:
                addr = self.bs4.find('input',attrs={'name':"myvs_13c"}).get('value')
                if '新校区' in addr or '主校区' in addr:
                    return zzu_geo_dict
                addr = self.bs4.find('input',attrs={'name':"myvs_13c"}).get('value')
                longitude = self.bs4.find('input',attrs={'name':"jingdu"}).get('value').replace(' ','')
                latitude = self.bs4.find('input',attrs={'name':"weidu"}).get('value').replace(' ','')
                if int(float(longitude)) == 0 and int(float(latitude)) == 0:
                    return zzu_geo_dict
                for i in self.bs4.find('select',attrs={'id':"myvs_13a"}).find_all('option'):
                    if 'selected' in i.attrs:
                        myvs_13a_value = i.get('value')
                        break
                for i in self.bs4.find('select',attrs={'id':"myvs_13b"}).find_all('option'):
                    if 'selected' in i.attrs:
                        myvs_13b_value = i.get('value')
                        break
            except:
                log.info('未能获取历史记录 ...')
            else:
                return {
                    'myvs_13a': myvs_13a_value,
                    'myvs_13b': myvs_13b_value,
                    'myvs_13c': addr,
                    'jingdu': longitude,
                    'weidu': latitude
                }
            return zzu_geo_dict

    def submit(self) -> bool:
        try:
            r = requests.post(self.submit_url, data=self.form_final, headers=self.headers)  # response为完成打卡页面
        except Exception as e:
            log.error(e)
        self.text = r.text.encode(r.encoding).decode(r.apparent_encoding)
        if ("感谢" in self.text and "今日上报健康状况" in self.text):
            return True
        else:
            log.error('验证码错误' if '验证码' in self.text else re.sub("[^\u4e00-\u9fa5]", '', self.text))
            return False

    def sign(self) -> bool:
        log.info(f"Preparing to sign for {self.name.title()} ...")
        if not self.login():
            log.error(f"{self.name.title()}登录失败 ...")
            return False
        else:
            if self.checkstatus():
                log.warning(f"{self.name}已经打过卡了，请不要重复打卡 ...")
            else:
                log.info('Processing address ...')
                self.prepare_form()
                if self.submit():
                    log.info(f"{self.name}健康打卡成功 ...")
                else:
                    log.error(f"{self.name}打卡失败 ...")
                    return False
            return True
