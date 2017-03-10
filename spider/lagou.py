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

        city_encoded = urllib.urlencode({'city': city.encode('utf-8')})
        url = 'https://www.lagou.com/jobs/positionAjax.json?{0}&needAddtionalResult=false'.format(
                city_encoded)
        utils.log('lagou url:%s' % url)

        data = {
            'first': 'true',
            'kd': query,
            'pn': page,
        }
        proxies = proxymng.get_proxy('lagou', '1')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }
        with open('spider/lagou_cookies.text', 'r') as f:
            cookies = f.read()
            f.close()
        cookies = json.loads(cookies)

        job_list = []
        try:
            r = requests.post(url = url, headers = headers, proxies = proxies, cookies = cookies, data = data,
                              timeout = 20)
            utils.log('lagou requests status:%s ok:%s' % (r.status_code, r.ok))

            try:
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
                        'query': query,
                        'city_name': param.get('city_name'),
                        'release_time': res.get('createTime'),
                    }
                    job_list.append(job)
            except Exception, e:
                utils.log('lagou parse data exception:%s city_name:%s query:%s' % (e, param.get('city_name'), query))
        except Exception, e:
            utils.log('lagou requests exception:%s' % e)

            proxymng.delete_proxy(self.name, proxies)

        return job_list


if __name__ == '__main__':
    reload(sys)
    sys.setdefaultencoding('utf-8')

    lagou = Lagou()
    utils.log(lagou.name)
    job_list = lagou.start_request(param = {})
    utils.log('job_list:%s' % job_list)
