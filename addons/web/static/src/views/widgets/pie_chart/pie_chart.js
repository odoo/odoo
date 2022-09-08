/** @odoo-module */

import { registry } from "@web/core/registry";
import { View } from "@web/views/view";
import { CallbackRecorder } from "@web/webclient/actions/action_hook";
import { standardWidgetProps } from "../standard_widget_props";

const { Component, useSubEnv } = owl;

export class PieChart extends Component {
    setup() {
        useSubEnv({
            __beforeLeave__: new CallbackRecorder(),
            __getGlobalState__: new CallbackRecorder(),
            __getLocalState__: new CallbackRecorder(),
            __getContext__: new CallbackRecorder(),
            __getOrderBy__: new CallbackRecorder(),
            config: { ...this.env.config, views: [] },
        });
    }

    get viewProps() {
        const { groupBy, measure, record } = this.props;
        const { fields, resId, resModel } = record;
        const context = { ...record.context };
        delete context.graph_mode;
        delete context.graph_measure;
        delete context.graph_groupbys;

        const { comparison, domain } = this.env.searchModel;
        const measureField = `<field name="${measure}" type="measure"/>`;
        const arch = `
            <graph type="pie">
                <field name="${groupBy.name}" interval="${groupBy.interval}"/>
                ${measure ? measureField : ""}
            </graph>`;
        return {
            type: "graph",
            resId,
            resModel,
            fields,
            context,
            domain,
            comparison,
            display: { controlPanel: false },
            arch,
        };
    }
}

PieChart.template = "web.PieChart";
PieChart.props = {
    ...standardWidgetProps,
    title: { type: String, optional: true },
    groupBy: { type: Object },
    measure: { type: String, optional: true },
};

PieChart.extractProps = ({ attrs }) => {
    const { groupby, measure } = attrs.modifiers;
    return {
        title: attrs.title,
        groupBy: {
            name: groupby.split(":")[0],
            interval: groupby.split(":")[1] || "",
        },
        measure,
    };
};

PieChart.components = {
    View,
};

registry.category("view_widgets").add("pie_chart", PieChart);
