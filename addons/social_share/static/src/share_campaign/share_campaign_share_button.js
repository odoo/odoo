/** @odoo-module **/

import { Component } from "@odoo/owl";

export class ShareBar extends Component {
    static template = "social_share.ShareBar";

    get encodedUrl() {
        return encodeURIComponent(this.url);
    }
    get postText() {
        return encodeURIComponent(this.props.postText);
    }
    get url() {
        return this.props.shareUrl;
    }

    _onShareLinkClick(event) {
        event.preventDefault();
        event.stopPropagation();
        window.open(
            event.target.href,
            event.target.target,
            "menubar=no,toolbar=no,resizable=yes,scrollbars=yes,height=550,width=600",
        );
    }
}
