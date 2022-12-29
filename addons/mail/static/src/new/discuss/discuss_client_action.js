/* @odoo-module */

import { Component } from "@odoo/owl";
import { Discuss } from "./discuss";

export class DiscussClientAction extends Component {
    static components = { Discuss };
    static props = ["*"];
    static template = "mail.discuss_client_action";
}
