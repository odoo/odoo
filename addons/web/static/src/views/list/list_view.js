/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { XMLParser, isAttr } from "@web/core/utils/xml";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { getActiveActions, processField } from "../helpers/view_utils";
import { ListRenderer } from "./list_renderer";
import { RelationalModel } from "../relational_model";

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
        this.visitXML(arch, (node) => {
            if (node.tagName === "field") {
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
            // if (node.tagName === "button") {
            //     columns.push({ type: "button" });
            // }
        });
        return { activeActions, fields: activeFields, columns };
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

        onWillStart(async () => {
            this.isExportEnable = await this.user.hasGroup("base.group_allow_export");
        });

        this.openRecord = this.openRecord.bind(this);

        useSubEnv({ model: this.model }); // do this in useModel?

        useSetupView({
            /** TODO **/
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
