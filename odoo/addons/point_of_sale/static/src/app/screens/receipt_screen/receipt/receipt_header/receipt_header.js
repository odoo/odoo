/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class ReceiptHeader extends Component {
    static template = "point_of_sale.ReceiptHeader";
    static props = {
        data: {
            type: Object,
            shape: {
                company: Object,
                header: { type: [String, { value: false }], optional: true },
                cashier: { type: String, optional: true },
                "*": true,
            },
        },
    };

    get vatText() {
        if (this.props.data.company.country?.vat_label) {
            return _t("%(vatLabel)s: %(vatId)s", {
                vatLabel: this.props.data.company.country.vat_label,
                vatId: this.props.data.company.vat,
            });
        }
        return _t("Tax ID: %(vatId)s", { vatId: this.props.data.company.vat });
    }
}
