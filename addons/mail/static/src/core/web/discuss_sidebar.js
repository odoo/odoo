/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";

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
        this.store = useStore();
    }

    get discussSidebarItems() {
        return discussSidebarItemsRegistry.getAll();
    }
}
