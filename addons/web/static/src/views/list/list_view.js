/** @odoo-module */

import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { isAttr, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { useViewButtons } from "@web/views/view_button/hook";
import { ViewButton } from "@web/views/view_button/view_button";
import { getActiveActions, processButton } from "../helpers/view_utils";
import { RelationalModel } from "../relational_model";
import { ListRenderer } from "./list_renderer";

const { onWillStart, useSubEnv } = owl.hooks;

export class ListViewHeaderButton extends ViewButton {
    async onClick() {
        const clickParams = this.props.clickParams;
        const { resModel, resIds } = await this.props.getInfo();

        clickParams.buttonContext = {
            active_domain: this.props.domain,
            active_id: resIds[0],
            active_ids: resIds,
            active_model: resModel,
        };

        this.trigger("action-button-clicked", {
            clickParams,
            record: { resModel, resIds },
        });
    }
}

export class GroupListArchParser extends XMLParser {
    parse(arch, fields) {
        const activeFields = {};
        const buttons = [];
        let buttonId = 0;
        this.visitXML(arch, (node) => {
            if (node.tagName === "button") {
                buttons.push({
                    ...processButton(node),
                    id: buttonId++,
                });
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, fields, "list");
                activeFields[fieldInfo.name] = fieldInfo;
            }
        });
        return { activeFields, buttons, fields };
    }
}

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
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let headerButtons = [];
        const groupListArchParser = new GroupListArchParser();
        let buttonGroup = undefined;
        const config = {};
        this.visitXML(arch, (node) => {
            if (node.tagName !== "button") {
                buttonGroup = undefined;
            }
            if (node.tagName === "button") {
                const button = {
                    ...processButton(node),
                    defaultRank: "btn-link",
                    type: "button",
                    id: buttonId++,
                };
                if (buttonGroup) {
                    buttonGroup.buttons.push(button);
                } else {
                    buttonGroup = {
                        type: "button_group",
                        buttons: [button],
                    };
                    columns.push(buttonGroup);
                }
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, fields, "list");
                activeFields[fieldInfo.name] = fieldInfo;
                if (isAttr(node, "invisible").falsy(true)) {
                    columns.push({
                        ...fieldInfo,
                        optional: node.getAttribute("optional") || false,
                        type: "field",
                    });
                }
            } else if (node.tagName === "groupby" && node.getAttribute("name")) {
                const fieldName = node.getAttribute("name");
                let { arch, fields: groupByFields } = fields[fieldName].views.groupby;
                groupByFields = Object.assign(
                    {
                        id: {
                            change_default: false,
                            company_dependent: false,
                            depends: [],
                            manual: false,
                            name: "id",
                            readonly: true,
                            required: false,
                            searchable: true,
                            sortable: true,
                            store: true,
                            string: "ID",
                            type: "integer",
                        },
                    },
                    groupByFields
                );
                const { activeFields, buttons, fields: parsedFields } = groupListArchParser.parse(
                    arch,
                    groupByFields
                );
                groupBy.buttons[fieldName] = buttons;
                groupBy.fields[fieldName] = { activeFields, fields: parsedFields };
                return false;
            } else if (node.tagName === "header") {
                headerButtons = [...node.children]
                    .map((node) => ({
                        ...processButton(node),
                        type: "button",
                        id: buttonId++,
                    }))
                    .filter((button) => !evaluateExpr(button.modifiersAttribute).invisible);
                return false;
            } else if (node.tagName === "tree") {
                config.limit = parseInt(node.getAttribute("limit"));
            }
        });

        return { activeActions, config, headerButtons, fields: activeFields, columns, groupBy };
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
            groupByInfo: this.archInfo.groupBy.fields,
            limit: this.archInfo.config.limit,
        });
        useViewButtons(this.model);

        onWillStart(async () => {
            this.isExportEnable = await this.user.hasGroup("base.group_allow_export");
        });

        this.openRecord = this.openRecord.bind(this);
        this.getInfo = this.getInfo.bind(this);

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

    async getInfo() {
        const root = this.model.root;
        const resModel = root.resModel;
        let resIds;
        if (root.isDomainSelected) {
            resIds = await this.model.orm.search(root.resModel, root.domain);
        } else {
            resIds = root.selection.map((r) => r.resId);
        }
        return {
            resIds,
            resModel,
        };
    }

    onSelectDomain() {
        this.model.root.selectDomain(true);
    }

    get nbSelected() {
        return this.model.root.selection.length;
    }

    get isPageSelected() {
        const root = this.model.root;
        return root.selection.length === root.records.length;
    }

    get isDomainSelected() {
        return this.model.root.isDomainSelected;
    }

    get nbTotal() {
        return this.model.root.count;
    }
}

ListView.type = "list";
ListView.display_name = "List";
ListView.icon = "fa-list-ul";
ListView.multiRecord = true;
ListView.components = { ListViewHeaderButton, ListRenderer, Layout, ViewButton };
ListView.props = {
    ...standardViewProps,
    hasSelectors: { type: Boolean, optional: 1 },
};
ListView.defaultProps = {
    hasSelectors: true,
};

ListView.template = `web.ListView`;
ListView.buttonTemplate = "web.ListView.Buttons";
ListView.ArchParser = ListArchParser;

registry.category("views").add("list", ListView);
