import { useService } from "@web/core/utils/hooks";
import { renderToElement } from "@web/core/utils/render";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { formatDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export async function handleSaleDetails(pos, hardwareProxy, dialog) {
    const saleDetails = await pos.data.call(
        "report.point_of_sale.report_saledetails",
        "get_sale_details",
        [false, false, false, [pos.session.id]]
    );
    const report = renderToElement(
        "point_of_sale.SaleDetailsReport",
        Object.assign({}, saleDetails, {
            date: formatDateTime(DateTime.now()),
            pos: pos,
            formatCurrency: pos.env.utils.formatCurrency,
        })
    );
    const result = await hardwareProxy.printer.printReceipt(report);
    if (!result.successful) {
        dialog.add(AlertDialog, {
            title: result.message.title,
            body: result.message.body,
        });
    }
    return result;
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
