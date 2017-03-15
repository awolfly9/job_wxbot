#-*- coding: utf-8 -*-

import json

import datetime
import requests
import sys
import urllib
import utils

from proxymanager import proxymng


class Lagou(object):
    name = 'lagou'

    def start_request(self, param):
        city = param.get('city_name', '上海')
        query = param.get('query', 'IOS')
        page = param.get('page', '1')
        is_use_proxy = param.get('is_use_proxy', True)

        city_encoded = urllib.urlencode({'city': city.encode('utf-8')})
        url = 'https://www.lagou.com/jobs/positionAjax.json?{0}&needAddtionalResult=false'.format(
                city_encoded)
        utils.log('lagou request url:%s' % url)
        data = {'first': 'true', 'kd': query, 'pn': page, }
        self.proxies = proxymng.get_proxy('lagou') if is_use_proxy else None
        with open('spider/lagou_cookies.text', 'r') as f:
            cookies = f.read()
            f.close()
        cookies = json.loads(cookies)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }

        for i in range(0, 3):
            r = self.request(url = url, headers = headers, cookies = cookies, data = data, proxies = self.proxies)
            if r != None and r.status_code == 200 and r.ok:  # 抓取信息成功
                return self.parse_data(r, param)
            else:
                if is_use_proxy:
                    # 如果抓取失败，则切换 代理 ip
                    proxymng.delete_proxy(self.name, self.proxies)
                    self.proxies = proxymng.get_proxy(self.name)

        utils.log('lagou request data Exception')
        return None

    def request(self, url, headers, cookies, data, proxies):
        try:
            r = requests.post(url = url, headers = headers, proxies = proxies, cookies = cookies, data = data,
                              timeout = 20)
            return r
        except Exception, e:
            utils.log('name:%s request exception:%s' % (self.name, e))

        return None

    def parse_data(self, r, param):
        job_list = []
        try:
            data = json.loads(r.text)
            content = data.get('content', '')
            presult = content.get('positionResult', '')
            result = presult.get('result', '')

            for i, res in enumerate(result):
                id = res.get('positionId', '')
                city_name = param.get('city_name', '')
                query = param.get('query', '')
                job_name = res.get('positionName', '')
                work_year = res.get('workYear', '')
                education = res.get('education', '')
                job_nature = res.get('jobNature', '')
                create_time = res.get('createTime', '')
                salary = res.get('salary', '')
                company_name = res.get('companyFullName', '')
                industry_field = res.get('industryField', '')
                finance_stage = res.get('financeStage', '')
                labels = res.get('companyLabelList', [])
                company_label = self.get_label(labels)
                company_size = res.get('companySize', '')
                labels = res.get('positionLables', [])
                job_label = self.get_label(labels)
                url = 'https://www.lagou.com/jobs/%s.html' % str(res.get('positionId'))

                job = {
                    'id': id,
                    'city_name': city_name,
                    'query': query,
                    'job_name': job_name,
                    'work_year': work_year,
                    'education': education,
                    'job_nature': job_nature,
                    'create_time': create_time,
                    'salary': salary,
                    'company_name': company_name,
                    'industry_field': industry_field,
                    'finance_stage': finance_stage,
                    'company_label': company_label,
                    'company_size': company_size,
                    'job_label': job_label,
                    'url': url,
                }

                job_list.append(job)
        except Exception, e:
            pass

        return job_list

    def get_label(self, labels):
        try:
            msg = ''
            for label in labels:
                msg = msg + label + ','
            return msg
        except:
            return ''


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')

    lagou = Lagou()
    utils.log(lagou.name)
    job_list = lagou.start_request(param = {})
    utils.log('job_list:%s' % job_list)
