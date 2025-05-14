import { Component } from "@odoo/owl";

export class ViewSwitcherBottomSheet extends Component {
    static template = "web.ViewSwitcherBottomSheet";
    static props = {
        views: { type: Array },
        switchView: { type: Function },
        activeViewType: { type: String },
        close: { type: Function, optional: true },
    };
}