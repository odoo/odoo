/** @odoo-module */

const { Component, onRendered } = owl;
import { _t } from "@web/core/l10n/translation";
import { NavBar } from "../NavBar/NavBar.js";
import { AlertMessage } from "../AlertMessage/AlertMessage.js";
export class CartView extends Component {
    setup() {
    }
    static components = { NavBar, AlertMessage }; 
}
CartView.template = 'CartView'
export default { CartView };

