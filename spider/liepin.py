#-*- coding: utf-8 -*-

import re
import requests
import sys
import utils

from bs4 import BeautifulSoup
from proxymanager import proxymng


class Liepin(object):
    name = 'liepin'

    def start_request(self, param):
        city = param.get('city_id', '010')
        query = param.get('query', 'IOS')
        page = param.get('page', '1')
        page = int(page) - 1

        url = 'https://www.liepin.com/zhaopin/?pubTime=&ckid=17c370b0a0111aa5&fromSearchBtn=2&compkind=&isAnalysis' \
              '=&init=-1&searchType=1&dqs=%s&industryType=&jobKind=&sortFlag=15&industries=&salary=&compscale' \
              '=&clean_condition=&key=%s&headckid=49963e122c30b827&curPage=%s' % (city, query, page)
        utils.log('liepin url:%s' % url)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }
        proxies = proxymng.get_proxy('liepin', '1')

        job_list = []
        try:
            r = requests.get(url = url, headers = headers, proxies = proxies, timeout = 20)
            utils.log('liepin requests status:%s ok:%s' % (r.status_code, r.ok))
            soup = BeautifulSoup(r.text, 'lxml')
            ul = soup.find(name = 'ul', attrs = {'class': 'sojob-list'})
            lis = ul.find_all(name = 'li')
            for li in lis:
                try:
                    job_name = li.div.div.span.a.text
                    job_name = self.replace(job_name)
                    job_condition = li.find(name = 'p', attrs = {'class': 'condition clearfix'}).get('title')
                    job_condition = self.replace(job_condition)
                    company_name = li.find(name = 'p', attrs = {'class': 'company-name'}).a.text
                    company_name = self.replace(company_name)
                    company_info = li.find(name = 'p', attrs = {'class': 'field-financing'}).text
                    company_info = self.replace(company_info)
                    url = li.div.div.span.a.get('href')

                    release_time = li.time.text

                    pattern = re.compile('\d+', re.S)
                    id = re.search(pattern, str(url)).group()

                    job = {
                        'job_name': job_name,
                        'job_condition': job_condition,
                        'company_name': company_name,
                        'company_info': company_info,
                        'url': url,
                        'id': id,
                        'city_name': param.get('city_name'),
                        'query': param.get('query'),
                        'release_time': release_time,
                    }
                    utils.log('job:%s' % job)
                    job_list.append(job)
                except Exception, e:
                    utils.log('liepin parse data exception:%s' % e)
                    continue
        except Exception, e:
            utils.log('liepin requests exception:%s' % e)

            proxymng.delete_proxy(self.name, proxies)

        return job_list

    def replace(self, data):
        data = data.replace(' ', '')
        data = data.replace('\n', '')
        data = data.replace('\t', '')
        return data


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')

    liepin = Liepin()
    utils.log(liepin.start_request(param = {}))
