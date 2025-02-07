/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { CopyButton } from "@web/core/copy_button/copy_button";

export class LinkTrackerWidget extends Component {
    static template = "website_links.LinkTrackerWidget";
    static components = { CopyButton };

    setup() {
        debugger;
    }
}

registry.category("view_widgets").add("link_tracker_copy_widget", LinkTrackerWidget);
