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
        this.doFullPrint = useTrackedAsync(() => this.pos.printReceipt({ order: this.order }));
        this.doBasicPrint = useTrackedAsync(() =>
            this.pos.printReceipt({ order: this.order, basic: true })
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
                label: _t("Print Receipt"),
                method: () => this.doFullPrint.call(),
                status: this.doFullPrint.status,
                icon: "fa-print",
                isPrimary: true,
            },
        ];
        if (this.pos.config.basic_receipt) {
            list[0].label = _t("Print Full Receipt");
            list.push({
                label: _t("Print Basic Receipt"),
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
