/* @odoo-module */

import { Component } from "@odoo/owl";

/**
 * @typedef {Object} Props
 * @property {string} date
 * @property {string} [className]
 */
export class DateSection extends Component {
    static template = "mail.DateSection";
    static props = ["date", "className?"];
}
