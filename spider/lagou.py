#-*- coding: utf-8 -*-

import json
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
        data = json.loads(r.text)
        content = data.get('content')
        result = content.get('positionResult').get('result')

        for i, res in enumerate(result):
            job = {
                'job_name': res.get('positionName'),
                'job_condition': res.get('education') + ' ' + res.get('workYear'),
                'company_name': res.get('companyFullName'),
                'company_info': res.get('financeStage'),
                'salary': res.get('salary'),
                'url': 'https://www.lagou.com/jobs/%s.html' % str(res.get('positionId')),
                'id': res.get('positionId'),
                'query': param.get('query'),
                'city_name': param.get('city_name'),
                'release_time': res.get('createTime'),
            }

            job_list.append(job)

        return job_list


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')

    lagou = Lagou()
    utils.log(lagou.name)
    job_list = lagou.start_request(param = {})
    utils.log('job_list:%s' % job_list)
