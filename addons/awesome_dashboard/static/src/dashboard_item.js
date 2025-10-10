import { Component } from "@odoo/owl";

export class DashboardItem extends Component {
    static template = "awesome_dashboard.DashboardItem"
    static props = {
        slots: Object,
        size: { type: Number, optional: true }
    };
}