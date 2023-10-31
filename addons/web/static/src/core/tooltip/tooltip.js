/** @odoo-module **/

const { Component } = owl;

export class Tooltip extends Component {}
Tooltip.template = "web.Tooltip";
Tooltip.props = {
    tooltip: { type: String, optional: true },
    template: { type: String, optional: true },
    info: { optional: true },
};
