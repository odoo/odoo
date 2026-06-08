import { Component } from "@odoo/owl";

export class InfoPopup extends Component {
    static template = "pos_self_order.InfoPopup";
    static props = {
        text: String,
        close: Function,
        buttons: Array,
    };
}
