#-*- coding: utf-8 -*-

import requests
import sys

from bs4 import BeautifulSoup


class Liepin(object):
    name = 'liepin'

    def start_request(self, param):
        reload(sys)
        sys.setdefaultencoding('utf-8')

        city = param.get('city_id', '010')
        query = param.get('query', 'IOS')
        page = param.get('page', '1')
        page = int(page) - 1

        url = 'https://www.liepin.com/zhaopin/?pubTime=&ckid=17c370b0a0111aa5&fromSearchBtn=2&compkind=&isAnalysis' \
              '=&init=-1&searchType=1&dqs=%s&industryType=&jobKind=&sortFlag=15&industries=&salary=&compscale' \
              '=&clean_condition=&key=%s&headckid=49963e122c30b827&curPage=%s' % (city, query, page)

        print('liepin url:%s' % url)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }
        r = requests.get(url = url, headers = headers, timeout = 10)
        # with open('liepin.html', 'w') as f:
        #     f.write(r.text)
        #     f.close()

        soup = BeautifulSoup(r.text, 'lxml')
        ul = soup.find(name = 'ul', attrs = {'class': 'sojob-list'})
        lis = ul.find_all(name = 'li')
        job_list = []
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

                job = {
                    'job_name': job_name,
                    'job_condition': job_condition,
                    'company_name': company_name,
                    'company_info': company_info,
                    'url': url
                }
                job_list.append(job)
            except:
                pass

        return job_list

    def replace(self, data):
        data = data.replace(' ', '')
        data = data.replace('\n', '')
        data = data.replace('\t', '')
        return data


if __name__ == '__main__':
    liepin = Liepin()
    print(liepin.start_request(param = {}))
