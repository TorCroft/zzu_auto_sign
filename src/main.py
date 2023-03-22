from .config import config, history as h
from .utils import SignException, delay, format_msg, log, notify_user,regularly_notify
from .core import sign_core

user_signed = []
user_unsigned = []
user_record = {}

def first_round():
    for user in config.active_users:
        for i in range(5):
            try:
                delay.custom_random_delay(config.sleep_interval)
                config.get_config(user)
                current_user = sign_core(config.name, config.uid, config.password, config.address, config.infected)
                if current_user.sign():
                    user_signed.append(user)
                    h.record(user,msg = '打卡成功 ...')
                else:
                    user_unsigned.append(user)
                    h.record(user, msg = f'打卡失败 ... 原因是{current_user.message}')
            except SignException:
                delay.custom_delay(600)
                if i == 4:
                    user_unsigned.append(user)
                    h.record(user, msg = f'打卡失败 ... 原因是{current_user.message}')
            else:
                break
    h.write()
    if not len(user_unsigned):
        return True
    else:
        log.info(f'{user_unsigned}没有成功打卡 ...')
        return False


def resign():
    log.info('First round failed. Initializing resign task ...')
    for _ in range(3):
        delay.custom_random_delay('300-600')
        list_copy = user_unsigned.copy()
        for user in list_copy:
            delay.custom_random_delay(config.sleep_interval)
            config.get_config(user)
            current_user = sign_core(config.name,config.uid, config.password, config.address, config.infected)
            if current_user.sign():
                h.record(user, msg = '健康打卡补签成功 ...')
                user_signed.append(user)
                user_unsigned.remove(user)
        if not len(user_unsigned):
            h.write()
            log.info("Resign task completed ...")
            return True


def send_failure_msg():
    notify_list = user_unsigned.copy()
    for count in range(5):
        notify_list_copy = notify_list.copy()
        for user in notify_list_copy:
            response = notify_user(user, format_msg(user))
            retcode = response['code']
            if retcode == 200:
                log.info(f'Message delivered to {config.name} ...')
                notify_list.remove(user)
        if not len(notify_list):
            log.info("Notification delivery completed ...")
            break
        elif count == 4:
            msg = f"{notify_list} didn't get notified ..."
            log.error(msg, response)
            notify_user('user0', "有没完成的通知推送", msg)
            break
        elif count > 0 and count < 4:
            delay.custom_random_delay('60-120')


def run_all():
    log.info('---------------Starting ...---------------')
    if first_round():
        log.info('Mission Completed ...')
    elif resign():
        log.info('Mission Completed ...')
    else:
        log.error('Mission Failed ...')
        send_failure_msg()
        return delay.pause_then_exit()
    regularly_notify()
    log.info('----------End of process run ...----------')
    return delay.pause_then_exit()
