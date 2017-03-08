#-*- coding: utf-8 -*-

import config

from scrapy import Selector
from bs4 import BeautifulSoup
from sqlhelper import SqlHelper

sql = SqlHelper()

command = (
    "CREATE TABLE IF NOT EXISTS {} ("
    "`id` INT(10) NOT NULL UNIQUE,"
    "`name` CHAR(10) NOT NULL,"
    "PRIMARY KEY(name)"
    ") ENGINE=InnoDB".format(config.boss_city_id_table))
sql.create_table(command)

with open('spider/boss.html', 'r') as f:
    text = f.read()
    f.close()

sel = Selector(text = text)

soup = BeautifulSoup(text, 'lxml')
s = soup.find(name = 'div', attrs = {'class': 'dorpdown-city'})

lis = s.find_all('li')
for li in lis:
    print('li data-val:%s  text:%s' % (li.attrs.get('data-val'), li.text))

    msg = (li.attrs.get('data-val'), li.text)
    command = ("INSERT IGNORE INTO {} (id, name) VALUES(%s, %s)".format(config.boss_city_id_table))

    sql.insert_data(command, msg)
