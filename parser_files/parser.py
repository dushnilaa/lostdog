import os
import re
import sys
import time
from datetime import datetime
import random

import requests
import yaml
from fake_useragent import UserAgent
from lxml import html
from dateutil.parser import parse

from db.methods import MethodsMySQL
from db.schemes import User


class Parser:
    def __init__(self):
        self.my_sql = MethodsMySQL()
        self.sleep_sec = self.read_yaml()[1]['sleep_sec']
        self.start_date = self.read_yaml()[1]['start_date']
        self.proxies = self.read_yaml()[1]['proxies']

    def read_yaml(self):
        with open(os.path.abspath(os.path.join(sys.argv[0], '../..', 'config.yaml'))) as fh:
            return yaml.safe_load(fh)

    @classmethod
    def dlt_n(cls, text):
        res = []
        for i in text:
            str_ = i.lstrip().rstrip()
            if str_ == '':
                continue
            res.append(str_)
        if not res:
            return None
        return ' '.join(res)

    def number_phone(self, part_phone, proxies=None):
        start_url = f'https://www.lost-dog.org/en-us/item_phone_view.php?{part_phone}'
        request = requests.get(url=start_url, proxies=proxies).text
        if request == '':
            return None
        time.sleep(self.sleep_sec)
        return request

    def parser_profile(self, start_url, headers=None, proxies=None):
        if headers:
            headers = {'User-Agent': UserAgent().chrome}
        request = requests.get(url=start_url, headers=headers, proxies=proxies).text

        tree = html.fromstring(request)

        if self.dlt_n(tree.xpath('//th[text()="Gender"]/../td//text()')) == 'Female':
            sex = 2
        elif self.dlt_n(tree.xpath('//th[text()="Gender"]/../td//text()')) == 'Male':
            sex = 1
        else:
            sex = 0
        if self.dlt_n(tree.xpath('//th[text()="Lost on"]/../td//text()')):
            happened = self.dlt_n(tree.xpath('//th[text()="Lost on"]/../td//text()'))
            dt = parse(happened)
            date = datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S")
            happened_at = datetime.timestamp(date)
            type_ = 1
        elif self.dlt_n(tree.xpath('//th[text()="Found on"]/../td//text()')):
            happened = self.dlt_n(tree.xpath('//th[text()="Found on"]/../td//text()'))
            dt = parse(happened)
            date = datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S")
            happened_at = datetime.timestamp(date)
            type_ = 2
        else:
            type_ = None
            happened_at = None

        lost_at = self.dlt_n(tree.xpath('//th[text()="Lost at"]/../td//text()'))
        desc = self.dlt_n(tree.xpath('//span[@style]/../text()'))
        author = self.dlt_n(tree.xpath('//th[text()="Name"]/../td//text()'))
        pics = [self.dlt_n(tree.xpath('//div[@class="blocPhotoAnnonce text-xs-center"]//img/@src'))]
        if pics == 'https://www.lost-dog.org/images/empty-chien-430x430.png':
            pics = []

        ws_id = start_url.split('/')[-1]
        find_item = re.findall(f"id_item={ws_id}&h=\S+',", request)
        part_link = find_item[0].replace("',", '')
        phone = self.number_phone(part_link, proxies=proxies)
        if phone is None:
            print(f'No profile number {start_url}')
            return

        dict_result = {
            'status': 0,
            'animal': 1,
            'type': type_,
            'sex': sex,
            'created_at': datetime.now().timestamp(),
            'happened_at': happened_at,
            'ws_id': ws_id,
            'website': 2,
            'phone': phone,
            'author': author,
            'address': lost_at,
            'descr': desc,
            'pics': pics,

        }
        self.my_sql.insert(dict_result, User)

    def parser_find(self, headers=None, proxies=None):
        if headers:
            headers = {'User-Agent': UserAgent().chrome}

        count = 1
        while True:

            start_url = f'https://www.lost-dog.org/en-us/search/us/{count}'
            request = requests.get(url=start_url, headers=headers, proxies=proxies).text

            tree = html.fromstring(request)
            links = tree.xpath('//a[@class="lienAnnonceOff"]/@href')
            dates = tree.xpath('//div[@class="col-xs-6 col-md-3 pr-0 text-xs-right btn-edit order2"]//span['
                               '@class="note"]//text()')[-1]
            print(links)
            for link in links:
                if self.proxies:
                    proxy = random.choice(self.proxies)
                    proxies = {
                        "http": f"http://{proxy}/",
                        "https": f"http://{proxy}/"
                    }
                self.parser_profile(link, proxies=proxies)
                time.sleep(self.sleep_sec)

            dt = parse(dates)
            date = datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S")
            end_date = datetime.timestamp(date)
            if end_date < time.time() - self.start_date:
                print('Парсинг успешно выполнен')
                break
            count += 1
            time.sleep(5)
