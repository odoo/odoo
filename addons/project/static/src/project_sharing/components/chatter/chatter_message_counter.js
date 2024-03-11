/** @odoo-module */

const { Component } = owl;

export class ChatterMessageCounter extends Component { }

ChatterMessageCounter.props = {
    count: Number,
};
ChatterMessageCounter.template = 'project.ChatterMessageCounter';
