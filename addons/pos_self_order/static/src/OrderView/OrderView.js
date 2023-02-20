/** @odoo-module */

const { Component, onRendered } = owl;
import { _t } from "@web/core/l10n/translation";
import { NavBar } from "../NavBar/NavBar.js";
import { formatMonetary } from "@web/views/fields/formatters";
export class OrderView extends Component {
    setup() {
    this.formatMonetary = formatMonetary;
    }
    static components = { NavBar }; 
}
OrderView.template = 'OrderView'
export default { OrderView };

