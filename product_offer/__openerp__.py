# -*- coding: utf-8 -*-
# Copyright 2017-2018 Quartile Limited
# Copyright 2017 eHanse
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Product Offer',
    'version': '8.0.1.6.0',
    'author': 'Quartile Limited, eHanse',
    'website': 'https://www.quartile.co',
    'category': 'Product',
    'depends': [
        'product',
        'sale_stock',
        'sale_line_quant_extended',
        'supplier_stock',
        'stock_reverse_owner',
    ],
    'description': """
    """,
    'data': [
        'views/product_template_views.xml',
    ],
    'post_init_hook': '_update_prod_tmpl_fields',
    'installable': True,
}
