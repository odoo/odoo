/* @odoo-module */

import { Component, useState } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export const discussSidebarItemsRegistry = registry.category("mail.discuss_sidebar_items");

/**
 * @typedef {Object} Props
 * @extends {Component<Props, Env>}
 */
export class DiscussSidebar extends Component {
    static template = "mail.DiscussSidebar";
    static props = {};
    static components = {};

    setup() {
        this.store = useState(useService("mail.store"));
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }
}
