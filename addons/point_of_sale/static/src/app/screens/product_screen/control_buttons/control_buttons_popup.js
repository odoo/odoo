/** @odoo-module */

import { Component } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class ControlButtonPopup extends Component {
    static template = "point_of_sale.ControlButtonPopup";
    static components = { Dialog };
}
