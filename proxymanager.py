#-*- coding: utf-8 -*-

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
            'https': 'https://%s:%s' % (proxy.get('ip'), proxy.get('port'))
        }

        return proxies

    def update_proxy(self):
        pass

    # TODO... 有需要再完善
    def delete_proxy(self, proxy):
        try:
            rets = proxy.split(':')
            ip = rets[1]
            ip = ip[2:]

            for item in self.proxys:
                if item.get('ip') == ip:
                    self.proxys.remove(item)
                    break

            if len(self.proxys) < 3:
                self.update_proxy()

            utils.log('--------------delete ip:%s-----------' % ip)
            r = requests.get(url = '%s/delete?name=%s&ip=%s' % (self.address, 'douban', ip))
            return r.text
        except:
            return False


proxymng = ProxyManager()
