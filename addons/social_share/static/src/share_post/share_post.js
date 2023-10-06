/** @odoo-module **/

import { registry } from "@web/core/registry";
import { ShareBar } from "@social_share/share_post/share_post_share_button";
import { ThankMessage } from "@social_share/share_post/thank_message";

import { Component, useState } from "@odoo/owl";

class SharePost extends Component {
    static components = {
        ShareBar,
        ThankMessage,
    };
    static template = "social_share.SharePost";

    setup() {
        this.state = useState({});
        this.busService = this.env.services.bus_service;
        if (this.props.targetId) {
            this.busService.addChannel(`social_share_link_target-${this.props.targetId}`);
            this.busService.subscribe("social_share/share_link_target", ({target_id, message}) => {
                console.log(target_id, message)
            });
        }
    }
}

registry.category("public_components").add("social_share_post", SharePost);
