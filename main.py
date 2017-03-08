#!/usr/bin/env python
# coding: utf-8

import datetime
import requests
import os
import sys
import config
import redis
import threading

from sqlhelper import SqlHelper
from spider.boss import Boss
from spider.lagou import Lagou
from wxbot import *

sql = SqlHelper()
red = redis.StrictRedis(host = 'localhost', port = 6379, db = 10)


class MyWXBot(WXBot):
    def run_wx(self):
        self.DEBUG = True
        self.conf['qr'] = 'png'
        self.is_big_contact = False  #如果确定通讯录过大，无法获取，可以直接配置，跳过检查。假如不是过大的话，这个方法可能无法获取所有的联系人
        self.is_login_success = False
        self.run()

    def find_job(self):
        while True:
            if self.is_login_success == False:
                time.sleep(3)
                continue

            job = red.lpop('job')
            if job == None:
                time.sleep(0.5)
                continue

            print('pop job:%s' % job)

            param = json.loads(job)
            platform = param.get('platform', '')
            platform_name = ''
            if platform == 'boss':
                full_msg = self.get_boss_job(param)
                platform_name = 'boss 直聘'
            elif platform == 'lagou':
                full_msg = self.get_lagou_job(param)
                platform_name = '拉钩网'
            else:
                full_msg = ''

            if full_msg != '' and full_msg != None:
                self.send_msg_by_uid('@%s %s \n%s' % (param.get('user_name'), platform_name, full_msg),
                                     param.get('user_id'))

                command = (
                    "INSERT IGNORE INTO {} (id, user_name, user_id, city, query, page, platform, result, save_time) "
                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)".format(config.user_query_table))

                msg = (
                    None, param.get('user_name'), param.get('user_id'), param.get('city_name', ''),
                    param.get('query', ''), 1, platform_name, full_msg, None)

                sql.insert_data(command, msg)
                time.sleep(2)

    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:
            self.send_msg_by_uid(u'hi', msg['user']['id'])
        elif msg['msg_type_id'] == 3 and msg['content']['type'] == 0:
            print('msg:%s' % msg)
            data = msg['content']['data']
            if u'@爱吃西瓜' in data:
                param = self.get_param(msg)
                if param != None:
                    self.get_all_job(param, msg)

    def get_all_job(self, param, msg):
        print('param:%s' % param)

        param['platform'] = 'boss'
        red.rpush('job', json.dumps(param))
        param['platform'] = 'lagou'
        red.rpush('job', json.dumps(param))

        print('red llen:%s' % str(red.llen('job')))

    def get_param(self, msg):
        desc = msg['content']['desc']

        # 这里解决在 pc 上发送 @ 消息，desc 没有和 data 一样保护 @ 信息的问题
        if u'@' in desc:
            desc = desc.replace(u'@爱吃西瓜 ', '')

        infos = desc.split(' ')

        if len(infos) >= 2:
            page = 1
            if len(infos) >= 3:
                try:
                    page = int(infos[2])
                except:
                    pass

            param = {
                'user_name': msg['content']['user']['name'],
                'user_id': msg['user']['id'],
                'platform': '',
                'city_name': infos[0],
                'query': infos[1],
                'page': page,
            }
            return param
        else:
            print('user:%s 格式不正确' % msg['user'])
            self.send_msg_by_uid('@%s 查询格式不正确' % (msg['content']['user']['name']), msg['user']['id'])

        return None

    def get_boss_job(self, param):
        command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(config.boss_city_id_table, param.get('city_name'))
        res = sql.query_one(command)
        if res != None:
            id = res[0]
            param['city_id'] = id

            boss = Boss()
            job_list = boss.start_request(param)
            full_msg = ''
            for job in job_list:
                job_name = job.get('job_name')
                job_condition = job.get('job_condition')
                company_name = job.get('company_name')
                company_info = job.get('company_info')
                url = job.get('url')

                info = '%s %s 招聘 %s %s 详情:%s\n\n' % (
                    company_name, company_info, job_name, job_condition, url)
                full_msg = full_msg + info

            return full_msg
        else:
            print('没有找到对应城市 id 城市名称:%s' % param.get('city_name'))
            self.send_msg_by_uid('@%s 没有找到对应城市 id, 城市名称:%s' % (param.get('user_name'), param.get('city_name')))

            '''
                def schedule(self):
                    self.send_msg(u'张三', u'测试')
                    time.sleep(1)
            '''

    def get_lagou_job(self, param):
        lagou = Lagou()
        job_list = lagou.start_request(param)
        full_msg = ''
        if len(job_list) > 0:
            for job in job_list:
                job_name = job.get('job_name')
                job_condition = job.get('job_condition')
                company_name = job.get('company_name')
                company_info = job.get('company_info')
                salary = job.get('salary')
                url = job.get('url')

                info = '%s %s 招聘 %s %s %s 详情:%s\n\n' % (
                    company_name, company_info, job_name, salary, job_condition, url)
                full_msg = full_msg + info
            return full_msg
        else:
            full_msg = '没有查询到相关工作,查询关键词:%s' % param.get('query')
            print('没有找到对应城市 id 城市名称:%s' % param.get('city_name'))
            self.send_msg_by_uid('@%s %s' % (param.get('user_name'), full_msg))

        return None


def main():
    if not os.path.exists('log'):
        os.makedirs('log')

    reload(sys)
    sys.setdefaultencoding('utf-8')

    # 创建用户查询记录表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(10) NOT NULL AUTO_INCREMENT UNIQUE,"
        "`user_name` CHAR(20) NOT NULL,"
        "`user_id` CHAR(200) NOT NULL,"
        "`city` CHAR(10) NOT NULL,"
        "`query` CHAR(20) NOT NULL,"
        "`page` INT(3) NOT NULL,"
        "`platform` CHAR(30) NOT NULL,"
        "`result` TEXT NOT NULL,"
        "`save_time` TIMESTAMP NOT NULL,"
        "PRIMARY KEY(id)"
        ") ENGINE=InnoDB".format(config.user_query_table))
    sql.create_table(command)

    wx = MyWXBot()

    t1 = threading.Thread(target = wx.run_wx)
    t2 = threading.Thread(target = wx.find_job)

    t1.start()
    t2.start()


if __name__ == '__main__':
    main()
