import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { standardActionServiceProps } from "@web/webclient/actions/action_plugin";

export class FsReportPlaceholder extends Component {
    static template = "account_fs_report.FsReportPlaceholder";
    static components = { ControlPanel };

    setup() {
        this.props = useProps(standardActionServiceProps);
    }

    get title() {
        return this.props.action.name || "";
    }
}

registry.category("actions").add("account_fs_report.placeholder", FsReportPlaceholder);
