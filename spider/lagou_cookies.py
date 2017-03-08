# coding: utf-8
'''
拉勾网爬虫
'''
from selenium import webdriver
import requests
from requests.exceptions import RequestException
import urllib
import time
import codecs
import json
import logging
import traceback
import os


class LagouSpider(object):
    def __init__(self, config):
        self.index_url = 'https://www.lagou.com'
        self.cookies = None
        self.delay_time = config.get('delay_time', 1)
        self.output_file = codecs.open(config.get('output', 'positions.txt'), 'w', encoding = 'utf-8')
        self.driver = webdriver.PhantomJS()
        self.init_cookies()
        self.logger = None
        self.init_logger()

    def init_cookies(self):
        '''
        初始化cookie
        :return:
        '''
        self.cookies = {
            'user_trace_token': None,
            'LGUID': None,
            'JSESSIONID': None,
            'index_location_city': '%E5%8C%97%E4%BA%AC',
            'TG-TRACK-CODE': 'search_code',
            '_ga': None,
            'LGSID': None,
            'LGRID': None,
            'SEARCH_ID': None
        }

    def init_logger(self):
        if os.path.exists('spider.log'):
            os.remove('spider.log')
        logging.basicConfig(filemode = 'w')
        self.logger = logging.getLogger('spider')
        self.logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler('spider.log')
        fh.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        fh_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        ch_formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(funcName)s - %(lineno)d - %(levelname)s - %(message)s")
        fh.setFormatter(fh_formatter)
        ch.setFormatter(ch_formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def crawl(self):
        self.get_position_type()

    def get_position_type(self):
        '''
        解析拉勾网首页，获取所有职位的label信息。
        拉钩网的职位有三个分类，比如Java相关的岗位，第一分类为“技术”，第二分类为“后端开发”，label为“Java”。
        '''
        types = []
        try:
            self.driver.get(self.index_url)
            menu_elements = self.driver.find_elements_by_xpath('//*[@id="sidebar"]/div[1]/div')
            for menu_element in menu_elements:
                first_type_element = menu_element.find_element_by_xpath('./div[1]')
                first_type_name = first_type_element.find_element_by_xpath('./h2').text
                second_type_elements = menu_element.find_elements_by_xpath('./div[2]/dl')
                for second_type_element in second_type_elements:
                    label_elements = second_type_element.find_elements_by_xpath('./dd/a')
                    for label_element in label_elements:
                        label_name = label_element.get_attribute('text')
                        types.append((first_type_name, second_type_element, label_name))
            for item in types:
                _, _, label_name = item
                self.get_position_list(label_name)
        except Exception as e:
            self.logger.error(e.message)

    def get_position_list(self, kd):
        '''
        获取职位列表
        首选访问https://www.lagou.com/jobs/allCity.html?keyword=职位的label&px=default获取城市信息，主要是为了获取
        cookie然后在调用接口
        '''
        kd_encoded = urllib.urlencode({'keyword': kd.encode('utf-8')})
        url = 'https://www.lagou.com/jobs/allCity.html?{0}&px=default'.format(kd_encoded)
        # js = 'window.open("https:{0}");'.format(url)
        self.driver.get(url)
        city_label_elements = self.driver.find_elements_by_xpath('//*[@id="main_container"]/div/div[1]/table[2]/tr')
        city_label_num = len(city_label_elements)
        try:
            for label_index in xrange(1, city_label_num + 1):
                city_elements = self.driver.find_elements_by_xpath(
                        '//*[@id="main_container"]/div/div[1]/table[2]/tr[{0}]/td[2]/ul/li'.format(label_index)
                )
                city_num = len(city_elements)
                for i in xrange(1, city_num + 1):
                    city_element = self.driver.find_element_by_xpath(
                            '//*[@id="main_container"]/div/div[1]/table[2]/tr[{0}]/td[2]/ul/li[{1}]'.format(label_index,
                                                                                                            i))
                    city_name = city_element.text.strip()
                    city_element.click()
                    for cookie in self.driver.get_cookies():
                        name = cookie['name']
                        if name in self.cookies:
                            self.cookies[name] = cookie['value']
                        elif name.startswith('Hm_lvt_') or name.startswith('Hm_lpvt_'):
                            self.cookies[name] = cookie['value']
                    with open('cookie_%s.text' % city_name, 'w') as f:
                        f.write(json.dumps(self.cookies, indent = 4))
                        f.close()

                    self.get_postions(kd, 'true', 1, city_name)
                    self.driver.back()
        except Exception as e:
            traceback.print_exc()
            self.logger.error(e.message)

    def get_postions(self, kd, first, pn, city):
        '''
        调用接口获取数据
        '''
        city_encoded = urllib.urlencode({'city': city.encode('utf-8')})
        url = 'https://www.lagou.com/jobs/positionAjax.json?px=default&{0}&needAddtionalResult=false'.format(
                city_encoded)
        data = {'kd': 'python', 'first': first, 'pn': pn}
        self.logger.info('{0} {1} {2}'.format(city.encode('utf-8'), kd.encode('utf-8'), pn))
        time.sleep(self.delay_time)
        try:
            response = requests.post(url, data = data, cookies = self.cookies, proxies = None)
            print('response:%s' % response.text)
            result = response.json()
            if result['code'] == 0:
                position_list = result['content']['positionResult']['result']
                self.write_file(position_list)
                # 如果获取的职位数据没有15条，那么就表示已经没有更多的数据了
                if len(position_list) == 15:
                    self.get_postions(kd, 'false', pn + 1, city)
        except RequestException as e:
            self.logger.error(e.message)
        except Exception as e:
            self.logger.error(e.message)

    def write_file(self, position_list):
        for position_data in position_list:
            self.output_file.write(json.dumps(position_data, ensure_ascii = False) + '\n')

    def __del__(self):
        self.output_file.close()
        self.driver.quit()


if __name__ == '__main__':
    config = {
        'delay_time': 1
    }
    spider = LagouSpider(config)
    spider.crawl()
