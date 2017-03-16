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
    # '''
    #     def schedule(self):
    #         self.send_msg(u'张三', u'测试')
    #         time.sleep(1)
    # '''
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
                time.sleep(1)
                continue

            utils.log('pop job:%s' % job)

            try:
                param = json.loads(job)
                platform = param.get('platform', '')
                platform_name = param.get('platform_name')
                if platform == 'boss':
                    msg = self.get_boss_local_job(param)
                elif platform == 'lagou':
                    msg = self.get_lagou_local_job(param)
                elif platform == 'liepin':
                    msg = self.get_liepin_local_job(param)
                else:
                    msg = ''

                if msg != '' and msg != None:
                    self.send_msg_by_uid('@%s %s \n%s' % (param.get('user_name'), platform_name, msg),
                                         param.get('user_id'))

                    command = (
                        "INSERT IGNORE INTO {} (id, user_name, user_id, city, query, page, platform, result, "
                        "save_time) "
                        "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)".format(config.user_query_table))

                    data = (
                        None, param.get('user_name'), param.get('user_id'), param.get('city_name', ''),
                        param.get('query', ''), 1, platform_name, msg, None)

                    sql.insert_data(command, data)
                    time.sleep(2)
            except Exception, e:
                self.send_msg_by_uid('用户查询信息失败  job:%s msg:%s' % (job, e))
                continue

    # 抓取招聘网站更新的消息，并发到微信群里面
    # def update_job(self):
    #     while True:
    #         if self.is_login_success == False:
    #             time.sleep(5)
    #             continue
    #
    #         try:
    #             self.update_boss_job()
    #             time.sleep(10)
    #             self.update_lagou_job()
    #             time.sleep(10)
    #             self.update_liepin_job()
    #             time.sleep(10)
    #         except Exception, e:
    #             utils.log('update job exception msg:%s' % e)
    #             self.send_msg_by_uid('')

    def crawl_boss_job(self):
        while True:
            if self.is_login_success == False:
                time.sleep(5)
                continue

            try:
                self.update_boss_job()
            except Exception, e:
                utils.log('update boss job exception msg:%s' % e)
                self.send_msg_by_uid('在抓取 Boss 直聘时出现中断异常 msg:%s' % e)

            time.sleep(60)

    def crawl_lagou_job(self):
        while True:
            if self.is_login_success == False:
                time.sleep(5)
                continue

            try:
                self.update_lagou_job()
            except Exception, e:
                utils.log('update lagou job exception msg:%s' % e)
                self.send_msg_by_uid('在抓取拉勾网时出现中断异常 msg:%s' % e)

            time.sleep(60)

    def crawl_liepin_job(self):
        while True:
            if self.is_login_success == False:
                time.sleep(5)
                continue

            try:
                self.update_liepin_job()
            except Exception, e:
                utils.log('update liepin job exception msg:%s' % e)
                self.send_msg_by_uid('在抓取猎聘时出现中断异常 msg:%s' % e)

            time.sleep(60)

    def handle_msg_all(self, msg):
        utils.log('msg:%s' % msg)
        if msg['msg_type_id'] == 4 and msg['content']['type'] == 0:
            # self.send_msg_by_uid(u'hi', msg['user']['id'])
            pass
        elif (msg['msg_type_id'] == 3 or msg['msg_type_id'] == 1) and msg['content']['type'] == 0:
            data = msg['content']['data']
            if u'@job' in data:
                param = self.get_param(msg)
                if param != None:
                    self.get_all_job(param, msg)

    def get_all_job(self, param, msg):
        utils.log('param:%s' % param)

        param['platform'] = 'boss'
        param['platform_name'] = 'boss 直聘'
        red.rpush('job', json.dumps(param))
        param['platform'] = 'lagou'
        param['platform_name'] = '拉勾网'
        red.rpush('job', json.dumps(param))
        param['platform'] = 'liepin'
        param['platform_name'] = '猎聘网'
        red.rpush('job', json.dumps(param))

        command = (
            "INSERT IGNORE INTO {} (id, user_name, user_id, city, query, page, platform, result, "
            "save_time) "
            "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)".format(config.user_query_table))

        data = (
            None, param.get('user_name'), param.get('user_id'), param.get('city_name', ''),
            param.get('query', ''), 1, '', '', None)

        sql.insert_data(command, data)

        utils.log('redis length:%s' % red.llen('job'))

    def get_param(self, msg):
        desc = msg['content']['desc']

        # 这里解决在 pc 上发送 @ 消息，desc 没有和 data 一样保护 @ 信息的问题
        if u'@' in desc:
            desc = desc.replace(u'@job ', '')

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
                'is_use_proxy': False,
            }
            return param
        else:
            utils.log('user:%s 格式不正确' % msg['user'])
            self.send_msg_by_uid('@%s 查询格式不正确' % (msg['content']['user']['name']), msg['user']['id'])

        return None

    def get_boss_local_job(self, param):
        table_name = '%s_job' % param.get('platform')
        command = "SELECT * FROM {0} WHERE job_name LIKE \'%{1}%\' AND city_name LIKE \'%{2}%\' ORDER BY save_time " \
                  "DESC limit 5".format(table_name, param.get('query'), param.get('city_name'))

        msg = ''
        result = sql.query(command)
        if result != None and len(result) > 0:
            for item in result:
                info = '{company_name} {company_info} 招聘 {job_name} {salary} {job_info} ' \
                       '{release_time} 详情:{url}\n\n'. \
                    format(company_name = item[7], company_info = item[8], job_name = item[3],
                           salary = item[6], job_info = item[4], release_time = item[5], url = item[10])
                msg = msg + info
        else:
            msg = '没有查询到数据, 查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
        return msg

    def get_lagou_local_job(self, param):
        table_name = '%s_job' % param.get('platform')
        command = "SELECT * FROM {0} WHERE job_name LIKE \'%{1}%\' AND city_name LIKE \'%{2}%\' ORDER BY save_time " \
                  "DESC limit 5".format(table_name, param.get('query'), param.get('city_name'))

        msg = ''
        result = sql.query(command)
        if result != None and len(result) > 0:
            for item in result:
                info = '{company_name} {finance_stage} 招聘 {job_name} {salary} {education}{work_year} {release_time} ' \
                       '详情:{url}\n\n'. \
                    format(company_name = item[9], finance_stage = item[11], job_name = item[3],
                           salary = item[8], education = item[5], work_year = item[4],
                           release_time = item[7], url = item[16])
                msg = msg + info
        else:
            msg = '没有查询到数据, 查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
        return msg

    def get_liepin_local_job(self, param):
        table_name = '%s_job' % param.get('platform')
        command = "SELECT * FROM {0} WHERE job_name LIKE \'%{1}%\' AND city_name LIKE \'%{2}%\' ORDER BY save_time " \
                  "DESC limit 5".format(table_name, param.get('query'), param.get('city_name'))

        msg = ''
        result = sql.query(command)
        if result != None and len(result) > 0:
            for item in result:
                info = '{company_name} {company_info} 招聘 {job_name} {job_condition} {release_time} ' \
                       '详情:{url}\n\n'. \
                    format(company_name = item[5], company_info = item[6], job_name = item[3], job_condition = item[4],
                           release_time = item[8], url = item[9])
                msg = msg + info
        else:
            msg = '没有查询到数据, 查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
        return msg

    def get_boss_job(self, param):
        msg = ''
        command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(
                config.boss_city_id_table, param.get('city_name'))
        res = sql.query_one(command)
        if res == None:
            msg = '没有找到对应城市 id， 城市名称:%s' % (param.get('city_name'))
        else:
            id = res[0]
            param['city_id'] = id

            boss = Boss()
            job_list = boss.start_request(param)
            if job_list == None:
                msg = '没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
            elif len(job_list) == 0:
                msg = '没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
            else:
                for job in job_list:
                    job_name = job.get('job_name')
                    job_info = job.get('job_info')
                    salary = job.get('salary')
                    company_name = job.get('company_name')
                    company_info = job.get('company_info')
                    url = job.get('url')
                    release_time = job.get('release_time')

                    info = '{company_name} {company_info} 招聘 {job_name} {salary} {job_info} ' \
                           '{release_time} 详情:{url}\n\n'. \
                        format(company_name = company_name, company_info = company_info, job_name = job_name,
                               salary = salary, job_info = job_info, release_time = release_time, url = url)
                    msg = msg + info
        return msg

    def get_lagou_job(self, param):
        msg = ''
        lagou = Lagou()
        job_list = lagou.start_request(param)
        if job_list == None:
            msg = '没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
        elif len(job_list) == 0:
            msg = '没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
        else:
            for job in job_list:
                job_name = job.get('job_name')
                company_name = job.get('company_name')
                finance_stage = job.get('finance_stage')
                education = job.get('education')
                work_year = job.get('work_year')
                salary = job.get('salary')
                url = job.get('url')
                release_time = job.get('release_time')

                info = '{company_name} {finance_stage} 招聘 {job_name} {salary} {education}{work_year} {release_time} ' \
                       '详情:{url}\n\n'. \
                    format(company_name = company_name, finance_stage = finance_stage, job_name = job_name,
                           salary = salary, education = education, work_year = work_year,
                           release_time = release_time, url = url)
                msg = msg + info

        return msg

    def get_liepin_job(self, param):
        msg = ''
        command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(
                config.liepin_city_id_table, param.get('city_name'))
        res = sql.query_one(command)
        if res == None:
            msg = '没有找到对应城市 id， 城市名称:%s' % (param.get('user_name'), param.get('city_name'))
        else:
            id = res[0]
            param['city_id'] = id

            liepin = Liepin()
            job_list = liepin.start_request(param)
            if job_list == None:
                msg = '没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
            elif len(job_list) == 0:
                msg = '没有查询到相关工作,查询城市:%s 查询关键词:%s' % (param.get('city_name'), param.get('query'))
            else:
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
                    msg = msg + info

        return msg

    def update_boss_job(self):
        cf = ConfigParser.ConfigParser()
        cf.read('job_conf.ini')
        citys = cf.get('boss', 'citys')
        querys = cf.get('boss', 'querys')
        for city in citys.split(','):
            command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(config.boss_city_id_table, city)
            res = sql.query_one(command)
            if res == None:
                continue

            city_id = res[0]
            for query in querys.split(','):
                param = {
                    'city_id': city_id,
                    'city_name': city,
                    'query': query,
                    'page': 1,
                }

                boss = Boss()
                job_list = boss.start_request(param)
                if job_list == None:
                    self.send_msg_by_uid('Boss 直聘，抓取数据异常 city:%s query:%s' % (city, query))
                elif len(job_list) == 0:
                    self.send_msg_by_uid('Boss 直聘，解析数据异常 city:%s query:%s' % (city, query))
                else:
                    for job in job_list:
                        id = job.get('id')

                        command = "SELECT id FROM {0} WHERE id = \'{1}'".format(config.boss_job_table, id)
                        res = sql.query_one(command)
                        # 这是一个新发布的招聘数据
                        if res == None:
                            query = job.get('query', '')
                            job_name = job.get('job_name', '')
                            job_info = job.get('job_info', '')
                            salary = job.get('salary', '')
                            company_name = job.get('company_name', '')
                            company_info = job.get('company_info', '')
                            release_time = job.get('release_time', '')
                            url = job.get('url')
                            job_label = job.get('job_label', '')

                            info = 'Boss 直聘 {city_name} {query}\n{company_name} {company_info} 招聘 {job_name}' \
                                   '{salary} {job_info} {release_time} 详情:{url}\n\n'. \
                                format(city_name = city, query = query,
                                       company_name = company_name, company_info = company_info, job_name = job_name,
                                       salary = salary, job_info = job_info, release_time = release_time, url = url)

                            self.send_msg('西瓜群', info)

                            command = (
                                "INSERT IGNORE INTO {} (id, city_name, query, job_name, job_info, "
                                "release_time, salary, company_name, company_info, job_label, url, job_jd, save_time) "
                                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".
                                    format(config.boss_job_table))

                            msg = (
                                id, city, query, job_name, job_info, release_time, salary, company_name,
                                company_info, job_label, url, '', None)

                            sql.insert_data(command, msg)

                            time.sleep(40)

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

                lagou = Lagou()
                job_list = lagou.start_request(param)
                if job_list == None:
                    self.send_msg_by_uid('Lagou 抓取数据失败 city:%s query:%s' % (city, query))
                elif len(job_list) == 0:
                    self.send_msg_by_uid('Lagou 没有解析到数据 city:%s query:%s' % (city, query))
                else:
                    for job in job_list:
                        id = job.get('id')

                        command = "SELECT id FROM {0} WHERE id = \'{1}'".format(config.lagou_job_table, id)
                        res = sql.query_one(command)
                        # 这是一个新发布的招聘数据
                        if res == None:
                            city_name = job.get('city_name', '')
                            query = job.get('query', '')
                            job_name = job.get('job_name', '')
                            work_year = job.get('work_year', '')
                            education = job.get('education', '')
                            job_nature = job.get('job_nature', '')
                            create_time = job.get('create_time', '')
                            salary = job.get('salary', '')
                            company_name = job.get('company_name', '')
                            industry_field = job.get('industry_field', '')
                            finance_stage = job.get('finance_stage', '')
                            company_label = job.get('company_label', '')
                            company_size = job.get('company_size', '')
                            job_label = job.get('job_label', '')
                            url = job.get('url')

                            info = '拉勾网 {city_name} {query}\n{company_name} {finance_stage} 招聘 {job_name} {salary} ' \
                                   '{education}{work_year} {release_time} 详情:{url}\n\n'. \
                                format(city_name = city, query = query, company_name = company_name,
                                       finance_stage = finance_stage, job_name = job_name,
                                       salary = salary, education = education, work_year = work_year,
                                       release_time = create_time, url = url)

                            self.send_msg('西瓜群', info)

                            command = (
                                "INSERT IGNORE INTO {} (id, city_name, query, job_name, work_year, education, "
                                "job_nature, create_time, salary, company_name, industry_field, finance_stage, "
                                "company_label, company_size, job_label, url, job_jd, save_time) "
                                "VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".
                                    format(config.lagou_job_table))

                            msg = (
                                id, city_name, query, job_name, work_year, education, job_nature, create_time, salary,
                                company_name, industry_field, finance_stage, company_label, company_size, job_label,
                                url, '', None)

                            sql.insert_data(command, msg)

                            time.sleep(40)

    def update_liepin_job(self):
        cf = ConfigParser.ConfigParser()
        cf.read('job_conf.ini')
        citys = cf.get('liepin', 'citys')
        querys = cf.get('liepin', 'querys')
        for city in citys.split(','):
            command = "SELECT * FROM {0} WHERE name LIKE \'{1}\'".format(config.liepin_city_id_table, city)
            res = sql.query_one(command)
            if res == None:
                continue

            city_id = res[0]
            for query in querys.split(','):
                param = {
                    'city_id': city_id,
                    'city_name': city,
                    'query': query,
                    'page': 1,
                }

                liepin = Liepin()
                job_list = liepin.start_request(param)
                if job_list == None:
                    self.send_msg_by_uid('liepin 抓取数据失败 city:%s query:%s' % (city, query))
                elif len(job_list) == 0:
                    self.send_msg_by_uid('liepin 没有解析到数据 city:%s query:%s' % (city, query))
                else:
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

                            time.sleep(40)


def init():
    # 创建用户查询记录表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(12) NOT NULL AUTO_INCREMENT UNIQUE,"
        "`user_name` CHAR(20) NOT NULL,"
        "`user_id` CHAR(200) DEFAULT NULL,"
        "`city` CHAR(10) DEFAULT NULL,"
        "`query` CHAR(20) DEFAULT NULL,"
        "`page` INT(3) DEFAULT NULL,"
        "`platform` CHAR(30) DEFAULT NULL,"
        "`result` TEXT DEFAULT NULL,"
        "`save_time` TIMESTAMP NOT NULL,"
        "PRIMARY KEY(id)"
        ") ENGINE=InnoDB".format(config.user_query_table))
    sql.create_table(command)

    # 创建 boss 直聘平台工作信息表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(10) NOT NULL UNIQUE,"
        "`city_name` CHAR(20) DEFAULT NULL,"
        "`query` CHAR(20) DEFAULT NULL,"
        "`job_name` CHAR(20) DEFAULT NULL,"
        "`job_info` CHAR(50) DEFAULT NULL,"
        "`release_time` CHAR(30) DEFAULT NULL,"
        "`salary` CHAR(20) DEFAULT NULL,"
        "`company_name` CHAR(100) DEFAULT NULL,"
        "`company_info` CHAR(200) DEFAULT NULL,"
        "`job_label` CHAR(100) DEFAULT NULL,"
        "`url` CHAR(100) DEFAULT NULL,"
        "`job_jd` TEXT DEFAULT NULL,"
        "`save_time` TIMESTAMP NOT NULL,"
        "PRIMARY KEY(id)"
        ") ENGINE=InnoDB".format(config.boss_job_table))
    sql.create_table(command)

    # 创建拉钩网平台工作信息表
    command = (
        "CREATE TABLE IF NOT EXISTS {} ("
        "`id` INT(10) NOT NULL UNIQUE,"
        "`city_name` CHAR(20) DEFAULT NULL,"
        "`query` CHAR(20) DEFAULT NULL,"
        "`job_name` CHAR(20) DEFAULT NULL,"
        "`work_year` CHAR(20) DEFAULT NULL,"
        "`education` CHAR(20) DEFAULT NULL,"
        "`job_nature` CHAR(20) DEFAULT NULL,"
        "`create_time` CHAR(30) DEFAULT NULL,"
        "`salary` CHAR(20) DEFAULT NULL,"
        "`company_name` CHAR(100) DEFAULT NULL,"
        "`industry_field` CHAR(100) DEFAULT NULL,"
        "`finance_stage` CHAR(100) DEFAULT NULL,"
        "`company_label` CHAR(100) DEFAULT NULL,"
        "`company_size` CHAR(100) DEFAULT NULL,"
        "`job_label` CHAR(100) DEFAULT NULL,"
        "`url` CHAR(100) DEFAULT NULL,"
        "`job_jd` TEXT DEFAULT NULL,"
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

    init()

    wx = MyWXBot()
    t1 = threading.Thread(target = wx.run_wx)
    t2 = threading.Thread(target = wx.user_query_job)
    t3 = threading.Thread(target = wx.crawl_boss_job)
    t4 = threading.Thread(target = wx.crawl_lagou_job)
    t5 = threading.Thread(target = wx.crawl_liepin_job)
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()
