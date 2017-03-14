#-*- coding: utf-8 -*-

import re
import requests
import sys
import utils

from bs4 import BeautifulSoup
from proxymanager import proxymng


class Boss(object):
    name = 'boss'

    def start_request(self, param):
        city = param.get('city_id', '101010100')
        query = param.get('query', 'python')
        page = param.get('page', '1')
        is_use_proxy = param.get('is_user_proxy', True)

        url = 'https://www.zhipin.com/c%s/h_%s/?query=%s&page=%s&ka=page-%s' % (city, city, query, page, page)
        utils.log('boss request url:%s' % url)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }
        self.proxies = proxymng.get_proxy(self.name) if is_use_proxy else None

        # 重试 3 次抓取
        for i in range(0, 3):
            r = self.request(url, headers, self.proxies)
            if r != None and r.status_code == 200 and r.ok:  # 抓取信息成功
                return self.parse_data(r, param)
            else:
                if is_use_proxy:
                    # 如果抓取失败，则切换 代理 ip
                    proxymng.delete_proxy(self.name, self.proxies)
                    self.proxies = proxymng.get_proxy(self.name)

        utils.log('boss request data Exception')
        return None

    def request(self, url, headers, proxies):
        try:
            r = requests.get(url = url, headers = headers, proxies = proxies, timeout = 20)
            return r
        except Exception, e:
            utils.log('name:%s request exception:%s' % (self.name, e))

        return None

    def parse_data(self, r, param):
        soup = BeautifulSoup(r.text, 'lxml')
        city = param.get('city_id', '101010100')
        query = param.get('query', 'python')
        page = param.get('page', '1')
        job_list = []

        page = int(page)
        for i in range((page - 1) * 15 + 1, page * 15 + 1):
            try:
                search = 'search_list_%s' % str(i)

                job_info = soup.find(attrs = {'ka': search})
                job_url = job_info.attrs.get('href', '')
                url = 'https://www.zhipin.com%s' % job_url
                pattern = re.compile('\d+', re.S)
                id = re.search(pattern, str(url)).group()

                primary = job_info.find(name = 'div', attrs = {'class': 'info-primary'})
                job_name = primary.h3.text

                job_condition = primary.p.text
                company = job_info.find(name = 'div', attrs = {'class': 'company-text'})
                company_name = company.h3.text
                company_info = company.p.text

                release_time = job_info.find(name = 'div', attrs = {'class': 'job-time'})
                release_time = release_time.text

                job = {
                    'job_name': job_name,
                    'job_condition': job_condition,
                    'company_name': company_name,
                    'company_info': company_info,
                    'release_time': release_time,
                    'query': query,
                    'city_name': param.get('city_name'),
                    'url': str(url),
                    'id': id,
                }

                # utils.log('job:%s' % job)

                job_list.append(job)
            except Exception, e:
                utils.log('boss parse data Exception:%s' % e)
                continue

        utils.log('boss job_list len:%s' % str(len(job_list)))
        return job_list


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')

    boss = Boss()
    utils.log(boss.name)
    job_list = boss.start_request(param = {})
    utils.log('job_list:%s' % job_list)
