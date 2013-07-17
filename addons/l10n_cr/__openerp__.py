# -*- encoding: utf-8 -*-
##############################################################################
#
#    __openerp__.py
#    l10n_cr_account
#    First author: Carlos Vásquez <carlos.vasquez@clearcorp.co.cr> (ClearCorp S.A.)
#    Copyright (c) 2010-TODAY ClearCorp S.A. (http://clearcorp.co.cr). All rights reserved.
#
#    Redistribution and use in source and binary forms, with or without modification, are
#    permitted provided that the following conditions are met:
#
#        1. Redistributions of source code must retain the above copyright notice, this list of
#          conditions and the following disclaimer.
#
#        2. Redistributions in binary form must reproduce the above copyright notice, this list
#          of conditions and the following disclaimer in the documentation and/or other materials
#          provided with the distribution.
#
#    THIS SOFTWARE IS PROVIDED BY <COPYRIGHT HOLDER> ``AS IS'' AND ANY EXPRESS OR IMPLIED
#    WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
#    FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
#    CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
#    CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
#    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
#    ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
#    NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
#    ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#    The views and conclusions contained in the software and documentation are those of the
#    authors and should not be interpreted as representing official policies, either expressed
#    or implied, of ClearCorp S.A..
#
##############################################################################

{
    'name': 'Costa Rica - Accounting',
    'version': '0.1',
    'url': 'http://launchpad.net/openerp-costa-rica',
    'author': 'ClearCorp S.A.',
    'website': 'http://clearcorp.co.cr',
    'category': 'Localization/Account Charts',
    'description': """
Chart of accounts for Costa Rica.
=================================

Includes:
---------
    * account.type
    * account.account.template
    * account.tax.template
    * account.tax.code.template
    * account.chart.template

Everything is in English with Spanish translation. Further translations are welcome,
please go to http://translations.launchpad.net/openerp-costa-rica.
    """,
    'depends': ['account', 'account_chart', 'base'],
    'demo': [],
    'data': [
        'l10n_cr_base_data.xml',
        'data/account_account_type.xml',
        'data/account_account_template.xml',
        'data/account_tax_code_template.xml',
        'data/account_chart_template.xml',
        'data/account_tax_template.xml',
        'l10n_wizard.xml',
    ],
    'license': 'Other OSI approved licence',
    'installable': True,
    'auto_install': False,
    'images': ['images/config_chart_l10n_cr.jpeg','images/l10n_cr_chart.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
