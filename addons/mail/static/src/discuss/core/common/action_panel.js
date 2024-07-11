/* @odoo-module */

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @prop {string} title
 * @prop {Object} [slots]
 * @extends {Component<Props, Env>}
 */
export class ActionPanel extends Component {
    static template = "mail.ActionPanel";
    static props = {
        title: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
}
