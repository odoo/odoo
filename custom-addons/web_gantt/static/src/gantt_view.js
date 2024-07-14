/* @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { scrollSymbol } from "@web/webclient/actions/action_hook";
import { GanttArchParser } from "./gantt_arch_parser";
import { GanttController } from "./gantt_controller";
import { GanttModel } from "./gantt_model";
import { GanttRenderer } from "./gantt_renderer";

const viewRegistry = registry.category("views");

export const ganttView = {
    type: "gantt",
    display_name: _t("Gantt"),
    icon: "fa fa-tasks",
    multiRecord: true,
    Controller: GanttController,
    Renderer: GanttRenderer,
    Model: GanttModel,
    ArchParser: GanttArchParser,
    searchMenuTypes: ["filter", "groupBy", "favorite"],
    buttonTemplate: "web_gantt.GanttView.Buttons",

    props: (genericProps, view, config) => {
        const modelParams = {};
        let scrollPosition;
        if (genericProps.state) {
            scrollPosition = genericProps.state[scrollSymbol];
            modelParams.metaData = genericProps.state.metaData;
        } else {
            const { arch, fields, resModel } = genericProps;
            const parser = new view.ArchParser();
            const archInfo = parser.parse(arch);

            let formViewId = archInfo.formViewId;
            if (!formViewId) {
                const formView = config.views.find((v) => v[1] === "form");
                if (formView) {
                    formViewId = formView[0];
                }
            }

            modelParams.metaData = {
                ...archInfo,
                fields,
                resModel,
                formViewId,
            };
        }

        return {
            ...genericProps,
            modelParams,
            Model: view.Model,
            Renderer: view.Renderer,
            buttonTemplate: view.buttonTemplate,
            scrollPosition,
        };
    },
};

viewRegistry.add("gantt", ganttView);
