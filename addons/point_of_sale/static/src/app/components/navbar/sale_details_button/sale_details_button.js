import { useService } from "@web/core/utils/hooks";
import { Component, props, types } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class SaleDetailsButton extends Component {
    static template = "point_of_sale.SaleDetailsButton";
    props = props({
        "isHeaderButton?": types.boolean(),
    });
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.dialog = useService("dialog");
    }

    async onClick() {
        await this.pos.ticketPrinter.printSaleDetailsReceipt();
    }
}
