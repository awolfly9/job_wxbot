#-*- coding: utf-8 -*-

import requests
import sys


class Liepin(object):
    def start_request(self, param):
        reload(sys)
        sys.setdefaultencoding('utf-8')

        url = 'https://www.liepin.com/zhaopin/?industries=&dqs=010&salary=&jobKind=&pubTime=&compkind=&compscale' \
              '=&industryType=&searchType=1&clean_condition=&isAnalysis=&init=1&sortFlag=15&flushckid=1&fromSearchBtn' \
              '=2&headckid=49963e122c30b827&key=python'
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:51.0) Gecko/20100101 Firefox/51.0',
        }
        r = requests.get(url = url, headers = headers, timeout = 10)
        with open('liepin.html', 'w') as f:
            f.write(r.text)
            f.close()


if __name__ == '__main__':
    liepin = Liepin()
    print(liepin.start_request(param = {}))
