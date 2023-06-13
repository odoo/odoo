odoo.define('pos_hr.CashierName', function (require) {
    'use strict';

    const CashierName = require('point_of_sale.CashierName');
    const Registries = require('point_of_sale.Registries');
    const SelectCashierMixin = require('pos_hr.SelectCashierMixin');
    const { useBarcodeReader } = require('point_of_sale.custom_hooks');

    const PosHrCashierName = (CashierName) =>
        class extends SelectCashierMixin(CashierName) {
            setup() {
                super.setup();
                useBarcodeReader({ cashier: this.barcodeCashierAction });
            }
            //@Override
            get avatar() {
                if (this.env.pos.config.module_pos_hr) {
                    const cashier = this.env.pos.get_cashier();
                    if (!(cashier && cashier.id)) {
                        return '';
                    }
                    return `/web/image/hr.employee/${cashier.id}/avatar_128`;
                }
                return super.avatar;
            }
        };

    Registries.Component.extend(CashierName, PosHrCashierName);

    return CashierName;
});
