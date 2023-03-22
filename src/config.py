import yaml
import os
from datetime import datetime, timedelta

project_path = os.path.dirname(os.path.join(os.getcwd(), ".."))

class Config:
    def __init__(self) -> None:
        self.active_users = []
        self.current_user = None
        self.all_users = self.load_user
        for i, user in self.all_users['users'].items():
            if user['status']:
                self.active_users.append(i)
        for i in self.all_users['admin']:
            self.__dict__[i] = self.all_users['admin'][i]
        self.is_expired = True if datetime.strptime(self.token_expire_date,'%Y/%m/%d %H:%M:%S') < self.cn_now else False

    @property
    def cn_now(self):
        return datetime.utcnow() + timedelta(hours=8)
    
    @property
    def load_user(self):
        self.config_file = os.path.join(project_path, 'config.yaml')
        with open(self.config_file, 'r', encoding='utf-8') as config:
            return yaml.safe_load(config)

    def get_config(self, user: str):
        self.current_user = user
        for i in self.all_users['users'][user]:
            self.__dict__[i] = self.all_users['users'][user][i]

    def save_token(self):
        self.all_users['admin']['ocr_access_token'] = self.ocr_access_token
        self.all_users['admin']['token_expire_date'] = (history.now + timedelta(days=29)).strftime('%Y/%m/%d %H:%M:%S')
        with open(self.config_file, 'w', encoding='utf-8') as con:
            yaml.dump(self.all_users, con, allow_unicode=True)


class History:
    '''
    云函数不开放写入权限，这个算是白写了:(
    '''
    def __init__(self) -> None:
        self.history_file = os.path.join(project_path, 'history.yaml')
        num = int(self.now.strftime('%w'))
        self.day_num = num if num else 7
        self.what_day = self.now.strftime('%a')
        self.history = {}
        old_history = self.load_history
        if old_history:
            self.history.update(old_history)

    @property
    def now(self):
        return datetime.utcnow() + timedelta(hours=8)

    @property
    def now_fmt(self):
        return self.now.strftime('%Y/%m/%d %a %H:%M:%S')

    @property
    def load_history(self):
        with open(self.history_file, 'r', encoding='utf-8') as history:
            return yaml.safe_load(history)

    def write(self):
        '''Save the changes you've made to history.yaml.'''
        with open(self.history_file, 'w', encoding='utf-8') as history:
            yaml.dump(self.history, history, allow_unicode=True)

    def record(self, user, **kwargs):
        data = {user :{
            f'log_{self.day_num}': {
                'date': self.now_fmt,
                **kwargs
            }
        }}
        try:
            self.history[user].update(data[user])
        except:
            self.history.update(data)

    def get_history(self, user):
        return self.history[user]

config = Config()
history = History()
