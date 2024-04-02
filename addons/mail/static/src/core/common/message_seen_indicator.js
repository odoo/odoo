import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import("models").Message} message
 * @property {import("models").Thread} thread
 * @extends {Component<Props, Env>}
 */
export class MessageSeenIndicator extends Component {
    static template = "mail.MessageSeenIndicator";
    static props = ["message", "thread", "className?"];
}
