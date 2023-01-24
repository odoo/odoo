/* @odoo-module */

import { Discuss } from "./discuss";

import { Component } from "@odoo/owl";

import { registry } from "@web/core/registry";

export class DiscussClientAction extends Component {
    static components = { Discuss };
    static props = ["*"];
    static template = "mail.discuss_client_action";
}

registry.category("actions").add("mail.action_discuss", DiscussClientAction);
