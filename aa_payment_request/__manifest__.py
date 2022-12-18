# -*- coding: utf-8 -*-
{
    'name': "Payment Request",

    'summary': """ Modul yang berfungsi untuk membuat approval permintaan pembayaran / pengeluaran uang """,

    'description': """
        Modul ini memiliki fitur :
        1. Approval Payment Request
        2. Approval Advance Payment
        3. Approval Settlement
    """,

    'author': "PT. Ismata Nusantara Abadi",

    'website': "https://ismata.co.id/",

    'category': 'Accounting/Accounting',

    'version': '0.1',

    'depends': ['base', 'account', 'mail', 'hr', 'om_account_accountant', 'account_reconciliation_widget'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],

    'application': True,
}
