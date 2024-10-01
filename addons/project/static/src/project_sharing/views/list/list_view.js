/** @odoo-module */

import { listView } from "@web/views/list/list_view";

import { ProjectSharingControlPanel } from '../../components/control_panel/project_sharing_control_panel';

const props = listView.props;
listView.props = function (genericProps, view) {
    const result = props(genericProps, view);
    return {
        ...result,
        allowSelectors: false,
    };
};

listView.ControlPanel = ProjectSharingControlPanel;
