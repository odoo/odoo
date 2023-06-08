/* @odoo-module */

import { Discuss } from "@mail/core/common/discuss";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class DiscussClientAction extends Component {
    static components = { Discuss };
    static props = ["*"];
    static template = "mail.DiscussClientAction";
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
