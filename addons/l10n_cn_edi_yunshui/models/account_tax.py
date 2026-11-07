# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_cn_vat_special_policy = fields.Selection(
        selection=[
            ('simplified', 'Simplified Taxation (简易征收)'),
            ('rare_earth', 'Rare Earth Products (稀土产品)'),
            ('exemption', 'Tax Exemption (免税)'),
            ('non_taxable', 'Non-taxable (不征税)'),
            ('collect_refund', 'Collect-then-refund (先征后退)'),
            ('collect_refund_100', '100% Collect-then-refund (100%先征后退)'),
            ('collect_refund_50', '50% Collect-then-refund (50%先征后退)'),
            ('simplified_3', '3% Simplified (按3%简易征收)'),
            ('simplified_5', '5% Simplified (按5%简易征收)'),
            ('simplified_5_1_5', '5%→1.5% Simplified (按5%简易征收减按1.5%计征)'),
            ('immediate_refund_30', '30% Immediate Refund (即征即退30%)'),
            ('immediate_refund_50', '50% Immediate Refund (即征即退50%)'),
            ('immediate_refund_70', '70% Immediate Refund (即征即退70%)'),
            ('immediate_refund_100', '100% Immediate Refund (即征即退100%)'),
            ('refund_gt_3', 'Refund >3% Burden (超税负3%即征即退)'),
            ('refund_gt_8', 'Refund >8% Burden (超税负8%即征即退)'),
            ('refund_gt_12', 'Refund >12% Burden (超税负12%即征即退)'),
            ('refund_gt_6', 'Refund >6% Burden (超税负6%即征即退)'),
            ('simplified_2', '2% Simplified (按2%简易征收)'),
            ('simplified_3_1_5', '3%→1.5% Simplified (按3%简易征收减按1.5%计征)'),
        ],
        string="VAT Special Policy",
        help="增值税特殊管理",
    )

    l10n_cn_free_tax_mark = fields.Selection(
        selection=[
            ('1', '1 Export & Other Tax Exemptions (出口免税和其他免税优惠政策)'),
            ('2', '2 No VAT (不征增值税)'),
            ('3', '3 General Zero Rate (普通零税率)'),
        ],
        string="Free Tax Mark",
        help="零税率标识",
    )

    l10n_cn_reduced_tax_code = fields.Selection(
        selection=[
            ('01', '01 Individual Housing Rental (个人出租住房)'),
            ('03', '03 Sale of Used Fixed Assets (销售自己使用过的固定资产)'),
            ('05', '05 Housing Rental (住房租赁)'),
        ],
        string="Reduced Tax Code",
        help="减按征税标识",
    )
