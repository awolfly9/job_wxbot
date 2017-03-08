#-*- coding: utf-8 -*-

import sys

import time
from selenium import webdriver
from scrapy import Selector
from sqlhelper import SqlHelper

sql = SqlHelper()

# command = (
#     "CREATE TABLE IF NOT EXISTS {} ("
#     "`id` CHAR(10) NOT NULL UNIQUE,"
#     "`name` CHAR(10) NOT NULL,"
#     "PRIMARY KEY(name)"
#     ") ENGINE=InnoDB".format('liepin_city_id'))
# sql.create_table(command)
#
# reload(sys)
# sys.setdefaultencoding('utf-8')
#
# url = 'https://www.liepin.com/zhaopin/?sfrom=click-pc_homepage-centre_searchbox-search_new&key=python'
#
# driver = webdriver.PhantomJS()
# driver.get(url = url)
# driver.save_screenshot('liepin.png')
# with open('liepin.html', 'w')  as f:
#     f.write(driver.page_source)
#     f.close()
#
# driver.find_element_by_xpath('//em[@class="drop"]').click()
# time.sleep(8)
#
# print('1')
#
# driver.save_screenshot('liepin_2.png')
# with open('liepin_2.html', 'w')  as f:
#     f.write(driver.page_source)
#     f.close()
#
# time.sleep(2)
#
# print('2')
#
# sel = Selector(text = driver.page_source)
# citys = sel.xpath('//div[@class="data-list"]/ul/li/a/@data-code').extract()
# # citys = driver.find_elements_by_xpath('//div[@class="data-list"]/ul/li/a/@data-code')
# print('3')
# for city in citys:
#     print('city:%s' % city)
#     driver.find_element_by_xpath('//a[@data-code="%s"]' % city).click()
#     time.sleep(4)
#
#     driver.save_screenshot('%s.png' % city)
#     with open('%s.html' % city, 'w')  as f:
#         f.write(driver.page_source)
#         f.close()
#
#     sel = Selector(text = driver.page_source)
#     cs = sel.xpath('//div[@class="data-list"]/ul/li/a').extract()
#     for c in cs:
#         s = Selector(text = c)
#         msg = (s.xpath('//@data-code').extract_first(), s.xpath('//text()').extract_first())
#         command = ("INSERT IGNORE INTO {} (id, name) VALUES(%s, %s)".format('liepin_city_id'))
#
#         sql.insert_data(command, msg)
#
#     driver.find_element_by_xpath('//li[@data-selector="tab-all"]').click()
#     time.sleep(4)


with open('liepin_2.html', 'r')  as f:
    text = f.read()
    f.close()

sel = Selector(text = text)
cs = sel.xpath('////li/a[@class="d-item"]').extract()
for c in cs:
    s = Selector(text = c)
    msg = (s.xpath('//@data-code').extract_first(), s.xpath('//text()').extract_first())
    command = ("INSERT IGNORE INTO {} (id, name) VALUES(%s, %s)".format('liepin_city_id'))

    sql.insert_data(command, msg)
