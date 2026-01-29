/** @odoo-module */

import { Component } from "@odoo/owl";

export class ProjectRightSidePanelSection extends Component { }

ProjectRightSidePanelSection.props = {
    name: { type: String, optional: true },
    header: { type: Boolean, optional: true },
    show: Boolean,
    showData: { type: Boolean, optional: true },
    slots: {
        type: Object,
        shape: {
            default: Object, // Content is not optional
            header: { type: Object, optional: true },
            title: { type: Object, optional: true },
        },
    },
    dataClassName: { type: String, optional: true },
    headerClassName: { type: String, optional: true },
};
ProjectRightSidePanelSection.defaultProps = {
    header: true,
    showData: true,
};

ProjectRightSidePanelSection.template = 'project.ProjectRightSidePanelSection';
