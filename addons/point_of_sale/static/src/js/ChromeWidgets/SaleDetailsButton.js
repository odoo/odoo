/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { ErrorPopup } from "../Popups/ErrorPopup";
import { Component } from "@odoo/owl";

export class SaleDetailsButton extends Component {
    static template = "SaleDetailsButton";

    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");
        this.orm = useService("orm");
        this.hardwareProxy = useService("hardware_proxy");
    }

    async onClick() {
        // IMPROVEMENT: Perhaps put this logic in a parent component
        // so that for unit testing, we can check if this simple
        // component correctly triggers an event.
        const saleDetails = await this.orm.call(
            "report.point_of_sale.report_saledetails",
            "get_sale_details",
            [false, false, false, [this.env.pos.pos_session.id]]
        );
        const report = renderToElement(
            "SaleDetailsReport",
            Object.assign({}, saleDetails, {
                date: new Date().toLocaleString(),
                pos: this.env.pos,
                formatCurrency: this.env.utils.formatCurrency,
            })
        );
        const { successful, message } = await this.hardwareProxy.printer.printReceipt(report);
        if (!successful) {
            await this.popup.add(ErrorPopup, {
                title: message.title,
                body: message.body,
            });
        }
    }
}
