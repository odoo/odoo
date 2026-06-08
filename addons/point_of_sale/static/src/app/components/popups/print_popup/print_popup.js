import { _t } from "@web/core/l10n/translation";
import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useTrackedAsync } from "@point_of_sale/app/hooks/hooks";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class PrintPopup extends Component {
    static template = "point_of_sale.PrintPopup";
    static components = { Dialog };
    static props = {
        order: Object,
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.ui = useService("ui");
        this.doFullPrint = useTrackedAsync(() =>
            this.pos.ticketPrinter.printOrderReceipt({ order: this.order })
        );
        this.doBasicPrint = useTrackedAsync(() =>
            this.pos.ticketPrinter.printOrderReceipt({ order: this.order, basic: true })
        );
        this.doSimplifiedPrint = useTrackedAsync(() =>
            this.pos.ticketPrinter.printOrderReceipt({ order: this.order, simplified: true })
        );
        if (this.printList.length === 1) {
            this.printList[0].method();
            this.props.close();
        }
    }

    get order() {
        return this.props.order;
    }

    get printList() {
        const list = [
            {
                label: _t("Full Receipt"),
                method: () => this.doFullPrint.call(),
                status: this.doFullPrint.status,
                icon: "fa-print",
                isPrimary: true,
            },
            {
                label: _t("Simplified Receipt"),
                method: () => this.doSimplifiedPrint.call(),
                status: this.doSimplifiedPrint.status,
                icon: "fa-file-text-o",
                isPrimary: false,
            },
        ];
        if (this.pos.config.basic_receipt) {
            list.push({
                label: _t("Gift Receipt"),
                method: () => this.doBasicPrint.call(),
                status: this.doBasicPrint.status,
                icon: "fa-gift",
                isPrimary: false,
            });
        }
        return list;
    }

    clickPrintButton(item) {
        item.method();
        this.props.close();
    }
}
