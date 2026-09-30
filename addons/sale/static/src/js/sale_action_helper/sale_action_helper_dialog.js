import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class SaleActionHelperDialog extends Component {
    static components = { Dialog };
    static template = "sale.SaleActionHelperDialog";
    static props = {
        url: String,
        close: Function,
    };
}
