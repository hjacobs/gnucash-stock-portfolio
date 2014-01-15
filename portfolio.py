#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import datetime
import logging
import requests

from bs4 import BeautifulSoup
from gnucash import Session, GncNumeric, ACCT_TYPE_STOCK
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
        if commodity.get_namespace() == 'BOND':
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


def update_quotes(s, args):
    book = s.book
    table = book.get_table()
    for namespace in table.get_namespaces_list():
        name = namespace.get_name()
        if name != 'CURRENCY':
            for commodity in namespace.get_commodity_list():
                update_quote(commodity, book)
    if not args.dry_run:
        s.save()


def report(s, args):
    book = s.book
    table = book.get_table()
    pricedb = book.get_price_db()
    # FIXME: hard-coded currency
    currency_code = 'EUR'
    currency = table.lookup('ISO4217', currency_code)
    account = book.get_root_account()
    for acc in account.get_descendants():
        if acc.GetType() == ACCT_TYPE_STOCK:
            commodity = acc.GetCommodity()
            namespace = commodity.get_namespace()
            if namespace != 'CURRENCY':
                print commodity.get_fullname(), commodity.get_cusip(), acc.GetBalance()
                inst = pricedb.lookup_latest(commodity, currency).get_value()
                print GncNumeric(instance=inst).to_string()


def add_commodity(s, args):
    raise NotImplementedError()


parser = argparse.ArgumentParser()
parser.add_argument('gnucash_file')
parser.add_argument('--dry-run', action='store_true', help='Do not write anything, noop-mode')
subparsers = parser.add_subparsers()
sp = subparsers.add_parser('update-quotes', help='Update stock quotes from online service')
sp.set_defaults(func=update_quotes)
sp = subparsers.add_parser('report', help='Print portfolio report')
sp.set_defaults(func=report)
sp = subparsers.add_parser('add-commodity', help='Helper method to add commodity by ISIN')
sp.add_argument('isin', help='ISIN of stock/bond to add')
sp.set_defaults(func=add_commodity)

args = parser.parse_args()

logging.basicConfig(level=logging.INFO)
logging.getLogger('urllib3').setLevel(logging.WARN)

s = Session(args.gnucash_file)
try:
    args.func(s, args)
finally:
    s.end()
