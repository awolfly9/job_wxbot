#-*- coding: utf-8 -*-
import re
import requests
import json
import utils
import random


class ProxyManager(object):
    def __init__(self):
        self.index = 0
        self.proxys = []

        self.update_proxy()

        self.address = 'http://127.0.0.1:8000'

    def get_proxy(self, name, anonymity = None, count = 100):
        if anonymity == None:
            url = '%s/select?name=%s&count=%s' % (self.address, name, count)
        else:
            url = '%s/select?name=%s&anonymity=%s&count=%s' % (self.address, name, anonymity, count)

        utils.log('get proxy url:%s' % url)

        r = requests.get(url = url, timeout = 10)
        data = json.loads(r.text)
        proxy = random.choice(data)

        proxies = {
            'http': 'http://%s:%s' % (proxy.get('ip'), proxy.get('port')),
            'https': 'http://%s:%s' % (proxy.get('ip'), proxy.get('port'))
        }

        utils.log('proxies:%s' % proxies)

        return proxies

    def update_proxy(self):
        pass

    def delete_proxy(self, name, proxies):
        try:
            http = proxies.get('http')
            pattern = re.compile('\d+[.]\d+[.]\d+[.]\d+', re.S)
            ip = re.search(pattern, http).group()

            utils.log('--------------delete name:%s ip:%s-----------' % (name, ip))
            r = requests.get(url = '%s/delete?name=%s&ip=%s' % (self.address, name, ip))
            return r.text
        except:
            return False


proxymng = ProxyManager()
