import { registry } from "@web/core/registry";
import { Component, useProps, t, onWillStart, providePlugins, useEffect } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ControlPanel } from "@web/search/control_panel/control_panel";

import { PosReportPlugin, usePosReport, SLOT_REPORT_HEADER } from "./pos_report_plugin";
import { PosReportFilters } from "./components/filters/filters";
import { Header } from "./components/header/header";
import { TreeNode } from "./components/tree_node/tree_node";

export class PosReport extends Component {
    static template = "pos_reports.PosReport";
    static components = {
        ControlPanel,
        PosReportFilters,
        Header,
        TreeNode,
    };
    props = useProps({
        action: t.object(),
    });

    setup() {
        providePlugins([PosReportPlugin], {
            action: this.props.action,
            ui: useService("ui"),
        });
        this.report = usePosReport();

        onWillStart(async () => {
            if (this.report.reportId) {
                await this.report.loadReport();
            }
        });

        useEffect(() => {
            const name = this.report.meta()?.name;
            if (name) {
                this.env.config.setDisplayName(name);
            }
        });
    }

    get headerExtensions() {
        return this.report.getExtensions(SLOT_REPORT_HEADER);
    }
}

registry.category("actions").add("pos_report", PosReport);
