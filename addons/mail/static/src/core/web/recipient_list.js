/* @odoo-module */

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {import('@mail/core/common/thread_model').Thread} thread
 * @property {function} [close]
 * @extends {Component<Props, Env>}
 */
export class RecipientList extends Component {
    static template = "mail.RecipientList";
    static props = ["thread", "close?"];
}
