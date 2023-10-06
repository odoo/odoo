/** @odoo-module **/

import { Component } from "@odoo/owl";

export class ShareBar extends Component {
    static template = "social_share.ShareBar";

    get url() {
        return this.props.shareUrl;
    }

    _onShareLinkClick(ev) {

        ev.preventDefault();
        ev.stopPropagation();

        const aEl = ev.currentTarget;

        const shareWindow = window.open(
            aEl.href,
            aEl.target,
            "menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600",
        );
    }
}
