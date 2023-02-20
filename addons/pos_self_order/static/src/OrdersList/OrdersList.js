/** @odoo-module */

const { Component, useState, useEffect, onWillStart } = owl;
import { _t } from "@web/core/l10n/translation";
import { OrderView } from "../OrderView/OrderView.js";

export class OrdersList extends Component {
    setup() {
    }
    static components = { OrderView };
}
OrdersList.template = 'OrdersList'
export default { OrdersList };

