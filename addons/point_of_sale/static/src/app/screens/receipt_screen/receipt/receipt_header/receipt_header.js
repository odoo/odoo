import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";

export class ReceiptHeader extends Component {
    static template = "point_of_sale.ReceiptHeader";
    static props = {
        order: Object,
    };

    get order() {
        return this.props.order;
    }

    get partnerAddress() {
        return this.order.partner_id?.pos_contact_address.split(/\n\n+/).join("\n").split("\n");
    }

    get vatText() {
        if (this.order.company.country_id?.vat_label) {
            return _t("%(vatLabel)s: %(vatId)s", {
                vatLabel: this.order.company.country_id.vat_label,
                vatId: this.order.company.vat,
            });
        }
        return _t("Tax ID: %(vatId)s", { vatId: this.order.company.vat });
    }
}
