import { Component } from "@odoo/owl";

export class JumpToPresentBanner extends Component {
    static template = "mail.JumpToPresentBanner";
    static props = ["jumpToPresent", "order"];
}
