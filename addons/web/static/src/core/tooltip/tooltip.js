/** @odoo-module **/

const { Component } = owl;

export class Tooltip extends Component {}
Tooltip.template = "web.Tooltip";
Tooltip.props = {
    tooltip: String,
};
