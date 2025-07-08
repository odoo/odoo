import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
export class CashierSelectionPopup extends Component {
    static template = "pos_hr.CashierSelectionPopup";
    static components = { Dialog };
    static props = {
        close: Function,
        getPayload: Function,
        currentCashier: { type: Object, optional: true },
        employees: { type: Array },
    };

    setup() {
        this.pos = usePos();
    }

    async lock() {
        await this.pos.showLoginScreen();
    }
    selectEmployee(employee) {
        this.props.getPayload(employee);
        this.props.close();
    }
}
