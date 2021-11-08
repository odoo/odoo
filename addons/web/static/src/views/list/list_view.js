/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { XMLParser, isAttr } from "@web/core/utils/xml";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { getActiveActions, processField } from "../helpers/view_utils";
import { ListRenderer } from "./list_renderer";
import { RelationalModel } from "../relational_model";
import { useViewButtons } from "@web/views/view_button/hook";

const { onWillStart } = owl.hooks;

const { useSubEnv } = owl.hooks;

export class ListArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const activeActions = {
            ...getActiveActions(xmlDoc),
            exportXlsx: isAttr(xmlDoc, "export_xlsx").truthy(true),
        };
        const activeFields = {};
        const columns = [];
        let buttonId = 0;
        this.visitXML(arch, (node) => {
            if (node.tagName === "button") {
                columns.push({
                    type: "button",
                    id: buttonId++,
                    icon: node.getAttribute("icon") || false,
                    title: node.getAttribute("string") || false,
                    clickParams: {
                        name: node.getAttribute("name"),
                        type: node.getAttribute("type") || "object",
                    },
                });
            } else if (node.tagName === "field") {
                if (isAttr(node, "invisible").falsy(true)) {
                    const fieldInfo = processField(node, fields, "list");
                    activeFields[fieldInfo.name] = fieldInfo;
                    columns.push({
                        ...fieldInfo,
                        optional: node.getAttribute("optional") || false,
                        type: "field",
                    });
                }
            }
        });

        function processColumns(unprocessedColumns) {
            const columns = [];
            unprocessedColumns.forEach((col) => {
                if (col.type === "button") {
                    if (columns.length && columns[columns.length - 1].type === "button_group") {
                        columns[columns.length - 1].buttons.push(col);
                    } else {
                        columns.push({
                            type: "button_group",
                            buttons: [col],
                        });
                    }
                } else {
                    columns.push(col);
                }
            });
            return columns;
        }

        return { activeActions, fields: activeFields, columns: processColumns(columns) };
    }
}

// -----------------------------------------------------------------------------

class ListView extends owl.Component {
    setup() {
        this.actionService = useService("action");
        this.user = useService("user");

        this.archInfo = new ListArchParser().parse(this.props.arch, this.props.fields);
        this.activeActions = this.archInfo.activeActions;
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            fields: this.props.fields,
            activeFields: this.archInfo.fields,
            viewMode: "list",
        });
        useViewButtons(this.model);

        onWillStart(async () => {
            this.isExportEnable = await this.user.hasGroup("base.group_allow_export");
        });

        this.openRecord = this.openRecord.bind(this);

        useSubEnv({ model: this.model }); // do this in useModel?

        useSetupView({
            /** TODO **/
        });

        usePager(() => {
            return {
                offset: this.model.root.offset,
                limit: this.model.root.limit,
                total: this.model.root.count,
                onUpdate: async ({ offset, limit }) => {
                    this.model.root.offset = offset;
                    this.model.root.limit = limit;
                    await this.model.root.load();
                    this.render();
                },
            };
        });
    }

    openRecord(record) {
        const resIds = this.model.root.records.map((datapoint) => datapoint.resId);
        this.actionService.switchView("form", { resId: record.resId, resIds });
    }

    onClickCreate() {
        this.actionService.switchView("form", { resId: undefined });
    }
}

ListView.type = "list";
ListView.display_name = "List";
ListView.icon = "fa-list-ul";
ListView.multiRecord = true;
ListView.components = { ListRenderer, Layout };
ListView.props = {
    ...standardViewProps,
    hasSelectors: { type: Boolean, optional: 1 },
};
ListView.defaultProps = {
    hasSelectors: true,
};

ListView.template = `web.ListView`;
ListView.buttonTemplate = "web.ListView.Buttons";

registry.category("views").add("list", ListView);
