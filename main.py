#!/usr/bin/env python
# coding: utf-8

import ConfigParser
import logging
import os
import sys
import config
import redis
import threading
import platform
import utils

from sqlhelper import SqlHelper
from spider.boss import Boss
from spider.lagou import Lagou
from spider.liepin import Liepin
from wxbot import *


class MyWXBot(WXBot):
    # 运行微信网页版
    def run_wx(self):
        self.DEBUG = True
        if 'Linux' in platform.platform():
            self.conf['qr'] = 'tty'
        else:
            self.conf['qr'] = 'png'
        self.is_big_contact = False  #如果确定通讯录过大，无法获取，可以直接配置，跳过检查。假如不是过大的话，这个方法可能无法获取所有的联系人
        self.is_login_success = False
        self.run()

    # 用户按照关键字查询工作
    def user_query_job(self):
        while True:
            if self.is_login_success == False:
                time.sleep(3)
                continue

            job = red.lpop('job')
            if job == None:
                time.sleep(0.5)
                continue

            utils.log('pop job:%s' % job)

            param = json.loads(job)
            platform = param.get('platform', '')
            platform_name = ''
            if platform == 'boss':
                full_msg = self.get_boss_job(param)
                platform_name = 'boss 直聘'
            elif platform == 'lagou':
                full_msg = self.get_lagou_job(param)
                platform_name = '拉钩网'
            elif platform == 'liepin':
                full_msg = self.get_liepin_job(param)
                platform_name = '猎聘网'
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

    # 抓取招聘网站更新的消息，并发到微信群里面
    def update_job(self):
        while True:
            if self.is_login_success == False:
                time.sleep(3)
                continue

            try:
                self.update_boss_job()
                time.sleep(10)
                self.update_lagou_job()
                time.sleep(10)
                self.update_liepin_job()
                time.sleep(10)
            except Exception, e:
                utils.log('update job exception msg:%s' % e)

    def handle_msg_all(self, msg):
        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:
            self.send_msg_by_uid(u'hi', msg['user']['id'])
        elif msg['msg_type_id'] == 3 and msg['content']['type'] == 0:
            utils.log('msg:%s' % msg)
            data = msg['content']['data']
            if u'@爱吃西瓜' in data:
                param = self.get_param(msg)
                if param != None:
                    self.get_all_job(param, msg)

    def get_all_job(self, param, msg):
        utils.log('param:%s' % param)

        param['platform'] = 'boss'
        red.rpush('job', json.dumps(param))
        param['platform'] = 'lagou'
        red.rpush('job', json.dumps(param))
        param['platform'] = 'liepin'
        red.rpush('job', json.dumps(param))

        utils.log('redis length:%s' % red.llen('job'))

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
            utils.log('user:%s 格式不正确' % msg['user'])
            self.send_msg_by_uid('@%s 查询格式不正确' % (msg['content']['user']['name']), msg['user']['id'])

        return None

    def get_boss_job(self, param):
        full_msg = ''
        try:
            command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(config.boss_city_id_table,
                                                                         param.get('city_name'))
            res = sql.query_one(command)
            if res != None:
                id = res[0]
                param['city_id'] = id

                boss = Boss()
                job_list = boss.start_request(param)
                if len(job_list) > 0:
                    for job in job_list:
                        job_name = job.get('job_name')
                        job_condition = job.get('job_condition')
                        company_name = job.get('company_name')
                        company_info = job.get('company_info')
                        url = job.get('url')

                        info = '{company_name} {company_info} 招聘 {job_name} {job_condition} {release_time} ' \
                               '详情:{url}\n\n'.format(company_name = company_name, company_info = company_info,
                                                     job_name = job_name, job_condition = job_condition,
                                                     release_time = job.get('release_time'), url = url)
                        full_msg = full_msg + info
                else:
                    msg = 'Boss 直聘 没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
                    utils.log(msg)
                    self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))
            else:
                msg = 'Boss 直聘 没有找到对应城市 id， 城市名称:%s' % param.get('city_name')
                utils.log(msg)
                self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))
        except:
            msg = 'Boss 直聘 查询失败，查询城市:%s, 查询关键词:%s' % (param.get('city_name'), param.get('query'))
            self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))

        return full_msg

    # '''
    #     def schedule(self):
    #         self.send_msg(u'张三', u'测试')
    #         time.sleep(1)
    # '''


    def get_lagou_job(self, param):
        full_msg = ''
        try:
            lagou = Lagou()
            job_list = lagou.start_request(param)

            if len(job_list) > 0:
                for job in job_list:
                    job_name = job.get('job_name')
                    job_condition = job.get('job_condition')
                    company_name = job.get('company_name')
                    company_info = job.get('company_info')
                    salary = job.get('salary')
                    url = job.get('url')

                    info = '{company_name} {company_info} 招聘 {job_name} {salary} {job_condition} {release_time} ' \
                           '详情:{url}\n\n'.format(company_name = company_name, company_info = company_info,
                                                 job_name = job_name, salary = salary,
                                                 job_condition = job_condition, release_time = job.get('release_time'),
                                                 url = url)
                    full_msg = full_msg + info
            else:
                msg = '拉勾网 没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
                utils.log(msg)
                self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))
        except:
            msg = '拉勾网 查询失败，查询城市:%s, 查询关键词:%s' % (param.get('city_name'), param.get('query'))
            self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))

        return full_msg

    def get_liepin_job(self, param):
        full_msg = ''
        try:
            command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(
                    config.liepin_city_id_table, param.get('city_name'))
            res = sql.query_one(command)
            if res != None:
                id = res[0]
                param['city_id'] = id

                liepin = Liepin()
                job_list = liepin.start_request(param)
                if len(job_list) > 0:
                    for job in job_list:
                        job_name = job.get('job_name')
                        job_condition = job.get('job_condition')
                        company_name = job.get('company_name')
                        company_info = job.get('company_info')
                        url = job.get('url')

                        info = '{company_name} {company_info} 招聘 {job_name} {job_condition} {release_time} ' \
                               '详情:{url}\n\n'.format(company_name = company_name, company_info = company_info,
                                                     job_name = job_name, job_condition = job_condition,
                                                     release_time = job.get('release_time'),
                                                     url = url)
                        full_msg = full_msg + info
                else:
                    msg = '猎聘网 没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
                    utils.log(msg)
                    self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))
            else:
                msg = '猎聘网 没有找到对应城市 id， 城市名称:%s' % param.get('city_name')
                utils.log(msg)
                self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))
        except:
            msg = '猎聘网 查询失败，查询城市:%s, 查询关键词:%s' % (param.get('city_name'), param.get('query'))
            self.send_msg_by_uid('@%s %s' % (param.get('user_name'), msg), param.get('user_id'))

        return full_msg

    def update_boss_job(self):
        cf = ConfigParser.ConfigParser()
        cf.read('job_conf.ini')
        citys = cf.get('boss', 'citys')
        querys = cf.get('boss', 'querys')
        for city in citys.split(','):
            command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(config.boss_city_id_table, city)
            res = sql.query_one(command)
            if res != None:
                city_id = res[0]
                for query in querys.split(','):
                    param = {
                        'city_id': city_id,
                        'city_name': city,
                        'query': query,
                        'page': 1,
                    }

                    try:
                        boss = Boss()
                        job_list = boss.start_request(param)
                        for job in job_list:
                            id = job.get('id')

                            command = "SELECT id FROM {0} WHERE id = \'{1}'".format(config.boss_job_table, id)
                            res = sql.query_one(command)
                            # 这是一个新发布的招聘数据
                            if res == None:
                                job_name = job.get('job_name')
                                job_condition = job.get('job_condition')
                                company_name = job.get('company_name')
                                company_info = job.get('company_info')
                                url = job.get('url')

                                info = 'Boss 直聘 {city_name} {query}\n{company_name} {company_info} 招聘 {job_name}' \
                                       '{job_condition} {release_time} 详情:{url}\n\n'.format(
                                        city_name = job.get('city_name'), query = job.get('query'),
                                        company_name = company_name, company_info = company_info, job_name = job_name,
                                        job_condition = job_condition,
                                        release_time = job.get('release_time'), url = url)

                                self.send_msg('西瓜群', info)

                                command = (
                                    "INSERT IGNORE INTO {} (id, city_name, query, job_name, job_condition, "
                                    "company_name, "
                                    "company_info, full_msg, release_time, url, save_time) "
                                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(config.boss_job_table))

                                msg = (
                                    id, job.get('city_name'), job.get('query'), job_name, job_condition, company_name,
                                    company_info, info, job.get('release_time'), url, None)

                                sql.insert_data(command, msg)

                                time.sleep(5)
                            else:
                                continue
                        time.sleep(5)
                    except Exception, e:
                        utils.log('boss crawl data exception:%s city_name:%s query:%s' % (e, city, query))
                        continue

    def update_lagou_job(self):
        cf = ConfigParser.ConfigParser()
        cf.read('job_conf.ini')
        citys = cf.get('lagou', 'citys')
        querys = cf.get('lagou', 'querys')
        for city in citys.split(','):
            for query in querys.split(','):
                param = {
                    'city_name': city,
                    'query': query,
                    'page': 1,
                }

                try:
                    lagou = Lagou()
                    job_list = lagou.start_request(param)
                    for job in job_list:
                        id = job.get('id')

                        command = "SELECT id FROM {0} WHERE id = \'{1}'".format(config.lagou_job_table, id)
                        res = sql.query_one(command)
                        # 这是一个新发布的招聘数据
                        if res == None:
                            job_name = job.get('job_name')
                            job_condition = job.get('job_condition')
                            company_name = job.get('company_name')
                            company_info = job.get('company_info')
                            salary = job.get('salary')
                            url = job.get('url')

                            info = '拉勾网 {city_name} {query}\n{company_name} {company_info} 招聘 {job_name} {salary}' \
                                   '{job_condition} {release_time} 详情:{url}\n\n'.format(
                                    city_name = job.get('city_name'), query = job.get('query'),
                                    company_name = company_name, company_info = company_info, job_name = job_name,
                                    salary = job.get('salary'), job_condition = job_condition,
                                    release_time = job.get('release_time'), url = url)

                            self.send_msg('西瓜群', info)

                            command = (
                                "INSERT IGNORE INTO {} (id, city_name, query, job_name, job_condition, company_name, "
                                "company_info, full_msg, release_time, url, save_time) "
                                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(config.lagou_job_table))

                            msg = (id, job.get('city_name'), job.get('query'), job_name, job_condition, company_name,
                                   company_info, info, job.get('release_time'), url, None)

                            sql.insert_data(command, msg)

                            time.sleep(5)
                        else:
                            continue
                    time.sleep(5)
                except Exception, e:
                    utils.log('lagou crawl data exception:%s city_name:%s query:%s' % (e, city, query))
                    continue

    def update_liepin_job(self):
        cf = ConfigParser.ConfigParser()
        cf.read('job_conf.ini')
        citys = cf.get('liepin', 'citys')
        querys = cf.get('liepin', 'querys')
        for city in citys.split(','):
            command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(config.liepin_city_id_table, city)
            res = sql.query_one(command)
            if res != None:
                city_id = res[0]
                for query in querys.split(','):
                    param = {
                        'city_id': city_id,
                        'city_name': city,
                        'query': query,
                        'page': 1,
                    }

                    try:
                        liepin = Liepin()
                        job_list = liepin.start_request(param)
                        for job in job_list:
                            id = job.get('id')

                            command = "SELECT id FROM {0} WHERE id = \'{1}'".format(config.liepin_job_table, id)
                            res = sql.query_one(command)
                            # 这是一个新发布的招聘数据
                            if res == None:
                                job_name = job.get('job_name')
                                job_condition = job.get('job_condition')
                                company_name = job.get('company_name')
                                company_info = job.get('company_info')
                                url = job.get('url')

                                info = '猎聘网 {city_name} {query}\n{company_name} {company_info} 招聘 {job_name} ' \
                                       '{job_condition} {release_time} 详情:{url}\n\n'.format(
                                        city_name = job.get('city_name'), query = job.get('query'),
                                        company_name = company_name, company_info = company_info, job_name = job_name,
                                        job_condition = job_condition, release_time = job.get('release_time'),
                                        url = url)

                                self.send_msg('西瓜群', info)

                                command = (
                                    "INSERT IGNORE INTO {} (id, city_name, query, job_name, job_condition, "
                                    "company_name, "
                                    "company_info, full_msg, release_time, url, save_time) "
                                    "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(
                                            config.liepin_job_table))

                                msg = (
                                    id, job.get('city_name'), job.get('query'), job_name, job_condition, company_name,
                                    company_info, info, job.get('release_time'), url, None)

                                sql.insert_data(command, msg)

                                time.sleep(5)
                            else:
                                continue
                        time.sleep(5)
                    except Exception, e:
                        utils.log('liepin crawl data exception:%s city_name:%s query:%s' % (e, city, query))
                        continue


def main():
    # 创建用户查询记录表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(12) NOT NULL AUTO_INCREMENT UNIQUE,"
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

    # 创建 boss 直聘平台工作信息表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(10) NOT NULL UNIQUE,"
        "`city_name` CHAR(20) NOT NULL,"
        "`query` CHAR(20) NOT NULL,"
        "`job_name` CHAR(200) NOT NULL,"
        "`job_condition` CHAR(200) NOT NULL,"
        "`company_name` CHAR(100) NOT NULL,"
        "`company_info` CHAR(200) NOT NULL,"
        "`full_msg` TEXT NOT NULL,"
        "`release_time` CHAR(30) NOT NULL,"
        "`url` CHAR(100) NOT NULL,"
        "`save_time` TIMESTAMP NOT NULL,"
        "PRIMARY KEY(id)"
        ") ENGINE=InnoDB".format(config.boss_job_table))
    sql.create_table(command)

    # 创建拉钩网平台工作信息表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(10) NOT NULL UNIQUE,"
        "`city_name` CHAR(20) NOT NULL,"
        "`query` CHAR(20) NOT NULL,"
        "`job_name` CHAR(200) NOT NULL,"
        "`job_condition` CHAR(200) NOT NULL,"
        "`company_name` CHAR(100) NOT NULL,"
        "`company_info` CHAR(200) NOT NULL,"
        "`full_msg` TEXT NOT NULL,"
        "`release_time` CHAR(30) NOT NULL,"
        "`url` CHAR(100) NOT NULL,"
        "`save_time` TIMESTAMP NOT NULL,"
        "PRIMARY KEY(id)"
        ") ENGINE=InnoDB".format(config.lagou_job_table))
    sql.create_table(command)

    # 创建猎聘网平台工作信息表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(10) NOT NULL UNIQUE,"
        "`city_name` CHAR(20) NOT NULL,"
        "`query` CHAR(20) NOT NULL,"
        "`job_name` CHAR(200) NOT NULL,"
        "`job_condition` CHAR(200) NOT NULL,"
        "`company_name` CHAR(100) NOT NULL,"
        "`company_info` CHAR(200) NOT NULL,"
        "`full_msg` TEXT NOT NULL,"
        "`release_time` CHAR(30) NOT NULL,"
        "`url` CHAR(100) NOT NULL,"
        "`save_time` TIMESTAMP NOT NULL,"
        "PRIMARY KEY(id)"
        ") ENGINE=InnoDB".format(config.liepin_job_table))
    sql.create_table(command)

    wx = MyWXBot()

    t1 = threading.Thread(target = wx.run_wx)
    t2 = threading.Thread(target = wx.user_query_job)
    t3 = threading.Thread(target = wx.update_job)

    t1.start()
    t2.start()
    t3.start()


if __name__ == '__main__':
    if not os.path.exists('log'):
        os.makedirs('log')

    if not os.path.exists('temp'):
        os.makedirs('temp')

    reload(sys)
    sys.setdefaultencoding('utf-8')

    logging.basicConfig(
            filename = 'log/job.log',
            format = '%(levelname)s %(asctime)s: %(message)s',
            level = logging.DEBUG
    )

    sql = SqlHelper()
    red = redis.StrictRedis(host = 'localhost', port = 6379, db = 10)

    main()

#
# if __name__ == '__main__':
#     logging.basicConfig(
#             filename = 'log/test.log',
#             format = '%(levelname)s %(asctime)s: %(message)s',
#             level = logging.DEBUG
#     )
#
#     lagou = Lagou()
#     # lagou.start_request(param = {})
#
#     cf = ConfigParser.ConfigParser()
#     cf.read('job_conf.ini')
#
#     citys = cf.get('boss', 'citys')
#     utils.log(citys)
#     for city in citys.split(','):
#         utils.log(city)
