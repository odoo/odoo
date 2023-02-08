/** @odoo-module */

import { useService } from "@web/core/utils/hooks";
import { renderToString } from "@web/core/utils/render";
import { ErrorPopup } from "../Popups/ErrorPopup";
import { Component } from "@odoo/owl";

export class SaleDetailsButton extends Component {
    static template = "SaleDetailsButton";

    setup() {
        super.setup(...arguments);
        this.popup = useService("popup");
        this.rpc = useService("rpc");
    }

    async onClick() {
        // IMPROVEMENT: Perhaps put this logic in a parent component
        // so that for unit testing, we can check if this simple
        // component correctly triggers an event.
        const saleDetails = await this.rpc({
            model: "report.point_of_sale.report_saledetails",
            method: "get_sale_details",
            args: [false, false, false, [this.env.pos.pos_session.id]],
        });
        const report = renderToString(
            "SaleDetailsReport",
            Object.assign({}, saleDetails, {
                date: new Date().toLocaleString(),
                pos: this.env.pos,
            })
        );
        const printResult = await this.env.proxy.printer.print_receipt(report);
        if (!printResult.successful) {
            await this.popup.add(ErrorPopup, {
                title: printResult.message.title,
                body: printResult.message.body,
            });
        }
    }
}
