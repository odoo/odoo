import { discussSidebarItemsRegistry } from "@mail/core/public_web/discuss_app/sidebar/sidebar";
import { DiscussSidebarCategory } from "@mail/discuss/core/public_web/discuss_app/sidebar/category";

import { Component } from "@odoo/owl";

import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebarCategories extends Component {
    static template = "mail.DiscussSidebarCategories";
    static props = {};
    static components = { DiscussSidebarCategory, Dropdown };

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.discusscorePublicWebService = useService("discuss.core.public.web");
        this.orm = useService("orm");
    }
}

discussSidebarItemsRegistry.add("channels", DiscussSidebarCategories, { sequence: 30 });
