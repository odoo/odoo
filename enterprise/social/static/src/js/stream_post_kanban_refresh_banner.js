/** @odoo-module **/

import { Component } from "@odoo/owl";

export class NewContentRefreshBanner extends Component {
    static template = "social.NewContentRefreshBanner";
    static props = [
        "refreshRequired",
        "onClickRefresh",
    ];
}
