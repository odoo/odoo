import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export async function handleSaleDetails(pos, hardwareProxy, dialog) {
    const saleDetails = await pos.data.call(
        "report.point_of_sale.report_saledetails",
        "get_sale_details",
        [false, false, false, [pos.session.id]]
    );
    const report = renderToElement(
        "point_of_sale.SaleDetailsReport",
        Object.assign({}, saleDetails, {
            date: new Date().toLocaleString(),
            pos: pos,
            formatCurrency: pos.env.utils.formatCurrency,
        })
    );
    try {
        if (hardwareProxy.printer) {
            const { successful, message } = await hardwareProxy.printer.printReceipt(report);
            if (!successful) {
                console.error("Error while printing sale details", message);
                await pos.downloadSessionReport(report);
            }
        } else {
            await pos.downloadSessionReport(report);
        }
    } catch (error) {
        console.error("Error while printing sale details", error);
    }
}
export class SaleDetailsButton extends Component {
    static template = "point_of_sale.SaleDetailsButton";
    static props = {
        isHeaderButton: { type: Boolean, optional: true },
    };
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
        this.hardwareProxy = useService("hardware_proxy");
    }

    async onClick() {
        await handleSaleDetails(this.pos, this.hardwareProxy, this.dialog);
    }
}
