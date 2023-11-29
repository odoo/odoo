/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/store/pos_hook";

export class SaleDetailsButton extends Component {
    static template = "point_of_sale.SaleDetailsButton";
    static props = {
        isHeaderButton: Boolean,
    };
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.hardwareProxy = useService("hardware_proxy");
    }

    async onClick() {
        // IMPROVEMENT: Perhaps put this logic in a parent component
        // so that for unit testing, we can check if this simple
        // component correctly triggers an event.
        const saleDetails = await this.pos.data.call(
            "report.point_of_sale.report_saledetails",
            "get_sale_details",
            [false, false, false, [this.pos.session.id]]
        );
        const report = renderToElement(
            "point_of_sale.SaleDetailsReport",
            Object.assign({}, saleDetails, {
                date: new Date().toLocaleString(),
                pos: this.pos,
                formatCurrency: this.env.utils.formatCurrency,
            })
        );
        const { successful, message } = await this.hardwareProxy.printer.printReceipt(report);
        if (!successful) {
            this.dialog.add(AlertDialog, {
                title: message.title,
                body: message.body,
            });
        }
    }
}
