#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import requests

from bs4 import BeautifulSoup
from gnucash import Session
from gnucash_patch import GncPrice


def get_quote_onvista_bond(isin):
    url = 'http://www.onvista.de/anleihen/snapshot.html?ISIN={}'.format(isin)
    r = requests.get(url)
    soup = BeautifulSoup(r.text)
    price = soup.select('.INHALT #KURSINFORMATIONEN ~ .t span:nth-of-type(2)')[0].contents
    print price


def get_quote_onvista_stock(isin):
    url = 'http://www.onvista.de/suche/?searchValue={}'.format(isin)
    r = requests.get(url)
    soup = BeautifulSoup(r.text)
    price = soup.select('.INHALT ul.KURSDATEN li:nth-of-type(1) span')[0].contents
    print price


parser = argparse.ArgumentParser()
parser.add_argument('gnucash_file')

args = parser.parse_args()
s = Session(args.gnucash_file)
try:
    book = s.book
    table = book.get_table()
    for namespace in table.get_namespaces_list():
        name = namespace.get_name()
        if name != 'CURRENCY':
            print name
            for commodity in namespace.get_commodity_list():
                print commodity.get_mnemonic()
                print commodity.get_fullname()
                isin = commodity.get_cusip()
                if len(isin) == 12:
                    try:
                        if name == 'BOND':
                            get_quote_onvista_bond(isin)
                        else:
                            get_quote_onvista_stock(isin)
                    except:
                        print 'failed to get quote'
finally:
    s.end()
