/** @odoo-module */

import { Component } from "@odoo/owl";

export class ChatterMessageCounter extends Component {
    static template = "project.ChatterMessageCounter";
    static props = {
        count: Number,
    };
}
