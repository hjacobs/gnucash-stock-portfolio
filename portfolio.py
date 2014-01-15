#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import datetime
import logging
import requests

from bs4 import BeautifulSoup
from gnucash import Session, GncNumeric
from gnucash_patch import GncPrice


def get_quote_onvista_bond(isin):
    url = 'http://www.onvista.de/anleihen/snapshot.html?ISIN={}'.format(isin)
    r = requests.get(url)
    soup = BeautifulSoup(r.text)
    price = soup.select('.INHALT #KURSINFORMATIONEN ~ .t span:nth-of-type(2)')[0].get_text()
    currency = 'EUR'
    logging.info('Got quote for %s: %s%%', isin, price)
    return GncNumeric(int(price.replace(',', '')), 100 * 100), currency


def get_quote_onvista_stock(isin):
    url = 'http://www.onvista.de/suche/?searchValue={}'.format(isin)
    r = requests.get(url)
    soup = BeautifulSoup(r.text)
    spans = soup.select('.INHALT ul.KURSDATEN li:nth-of-type(1) span')
    price = spans[0].get_text()
    currency = str(spans[1].get_text())
    logging.info('Got quote for %s: %s %s', isin, price, currency)
    return GncNumeric(int(price.replace(',', '')), 1000), currency


def update_quote(commodity, book):
    fullname = commodity.get_fullname()
    mnemonic = commodity.get_mnemonic()
    isin = commodity.get_cusip()
    if len(isin) != 12:
        return
    logging.info('Processing %s (%s, %s)..', fullname, mnemonic, isin)
    value, currency = None, None
    try:
        if name == 'BOND':
            value, currency = get_quote_onvista_bond(isin)
        else:
            value, currency = get_quote_onvista_stock(isin)
    except:
        logging.exception('Failed to get quote for %s', isin)
    if value and currency:
        table = book.get_table()
        gnc_currency = table.lookup('ISO4217', currency)
        p = GncPrice(book)
        p.set_time(datetime.datetime.now())
        p.set_commodity(commodity)
        p.set_currency(gnc_currency)
        p.set_value(value)
        book.get_price_db().add_price(p)


parser = argparse.ArgumentParser()
parser.add_argument('gnucash_file')
parser.add_argument('--dry-run', action='store_true', help='Do not write anything, noop-mode')

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARN)

s = Session(args.gnucash_file)
try:
    book = s.book
    table = book.get_table()
    for namespace in table.get_namespaces_list():
        name = namespace.get_name()
        if name != 'CURRENCY':
            for commodity in namespace.get_commodity_list():
                update_quote(commodity, book)
    if not args.dry_run:
        s.save()
finally:
    s.end()
