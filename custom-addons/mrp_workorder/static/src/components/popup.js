/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";

export class SelectionPopup extends Component {
    static components = { Dialog };

    get title() {
        return this.props.popupData.title;
    }

    get list() {
        return this.props.popupData.list;
    }

    async cancel() {
        await this.props.onClosePopup('SelectionPopup', true);
    }

    async selectItem(id) {
        await this.props.onSelectEmployee(id);
    }
}
SelectionPopup.props = {
    popupData: Object,
    onClosePopup: Function,
    onSelectEmployee: Function,
};
SelectionPopup.template = 'mrp_workorder.SelectionPopup';
