#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Monkey patch for GnuCash Python bindings as the Python class GncPrice does not implement a correct __init__ method by default
'''

import datetime
import gnucash.gnucash_core_c
from gnucash.function_class import ClassFromFunctions
from gnucash import Session, GncPrice, GncNumeric


def create_price(self, book=None, instance=None):
    if instance:
        price_instance = instance
    else:
        price_instance = gnucash.gnucash_core_c.gnc_price_create(book.get_instance())
    ClassFromFunctions.__init__(self, instance=price_instance)


GncPrice.__init__ = create_price

if __name__ == '__main__':
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.gnucash', delete=False) as fd:
        print fd.name
        s = Session(fd.name, is_new=True)
        commod_tab = s.book.get_table()
        currency = commod_tab.lookup('ISO4217', 'USD')
        p = GncPrice(s.book)
        p.set_time(datetime.datetime.now())
        p.set_commodity(currency)
        p.set_currency(commod_tab.lookup('ISO4217', 'EUR'))
        p.set_value(GncNumeric(123))
        s.book.get_price_db().add_price(p)
        s.save()
        s.end()
