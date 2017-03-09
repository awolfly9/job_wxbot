#-*- coding: utf-8 -*-

import json
import requests
import sys
import urllib
import utils


class Lagou(object):
    name = 'lagou'

    def start_request(self, param):
        reload(sys)
        sys.setdefaultencoding('utf-8')

        city = param.get('city_name', '上海')
        query = param.get('query', 'IOS')
        page = param.get('page', '1')

        city_encoded = urllib.urlencode({'city': city.encode('utf-8')})
        url = 'https://www.lagou.com/jobs/positionAjax.json?{0}&needAddtionalResult=false'.format(
                city_encoded)
        utils.log('lagou url:%s' % url)

        data = {
            'first': 'true',
            'kd': query,
            'pn': page,
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }

        with open('spider/lagou_cookies.text', 'r') as f:
            cookies = f.read()
            f.close()

        cookies = json.loads(cookies)

        r = requests.post(url = url, headers = headers, cookies = cookies, data = data, timeout = 100)
        data = json.loads(r.text)
        content = data.get('content')
        result = content.get('positionResult').get('result')

        job_list = []
        for i, res in enumerate(result):
            job = {
                'job_name': res.get('positionName'),
                'job_condition': res.get('education') + ' ' + res.get('workYear'),
                'company_name': res.get('companyFullName'),
                'company_info': res.get('financeStage'),
                'salary': res.get('salary'),
                'url': 'https://www.lagou.com/jobs/%s.html' % str(res.get('positionId'))
            }
            # utils.log('job:%s' % job)
            job_list.append(job)

        return job_list


if __name__ == '__main__':
    lagou = Lagou()
    utils.log(lagou.name)
    job_list = lagou.start_request(param = {})
    utils.log('job_list:%s' % job_list)
