#-*- coding: utf-8 -*-

import requests
import sys
import utils

from bs4 import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf-8')


class Boss(object):
    name = 'boss'

    def start_request(self, param):
        city = param.get('city_id', '101010100')
        query = param.get('query', 'python')
        page = param.get('page', '1')

        url = 'https://www.zhipin.com/c%s/h_%s/?query=%s&page=%s&ka=page-%s' % (city, city, query, page, page)
        utils.log('boss request url:%s' % url)

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }

        r = requests.get(url = url, headers = headers, timeout = 20)
        # with open('boss.html', 'w') as f:
        #     f.write(r.text)
        #     f.close()

        soup = BeautifulSoup(r.text, 'lxml')

        job_list = []

        page = int(page)
        for i in range((page - 1) * 15, page * 15 + 1):
            try:
                search = 'search_list_%s' % str(i)

                job_info = soup.find(attrs = {'ka': search})
                job_url = job_info.attrs.get('href', '')

                primary = job_info.find(name = 'div', attrs = {'class': 'info-primary'})
                job_name = primary.h3.text

                job_condition = primary.p.text
                company = job_info.find(name = 'div', attrs = {'class': 'company-text'})
                company_name = company.h3.text
                company_info = company.p.text

                job = {
                    'job_name': job_name,
                    'job_condition': job_condition,
                    'company_name': company_name,
                    'company_info': company_info,
                    'url': 'https://www.zhipin.com%s' % job_url
                }

                job_list.append(job)
            except:
                continue

        return job_list


if __name__ == '__main__':
    boss = Boss()
    utils.log(boss.name)
    job_list = boss.start_request(param = {})
    utils.log('job_list:%s' % job_list)
