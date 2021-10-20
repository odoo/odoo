/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { XMLParser } from "@web/core/utils/xml";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { Layout } from "@web/views/layout";
import { FieldParser } from "../helpers/view_utils";
import { RelationalModel } from "../relational_model";
import { ListRenderer } from "./list_renderer";

const { onWillStart } = owl.hooks;

const { useSubEnv } = owl.hooks;

export class ListArchParser extends XMLParser {
    parse(arch, fields) {
        const fieldParser = new FieldParser(fields, "list");
        const xmlDoc = this.parseXML(arch);
        const activeActions = this.getActiveActions(xmlDoc);
        this.visitXML(arch, (node) => {
            if (node.tagName === "field") {
                if (
                    this.isAttr(node, "invisible").falsy(true) &&
                    this.isAttr(node, "optional").notEqualTo("hide")
                ) {
                    fieldParser.addField(node, (fieldName) => {
                        const sortable = fields[fieldName].sortable;
                        const string = node.getAttribute("string") || fields[fieldName].string;
                        const widget = node.getAttribute("widget") || null;
                        return {
                            type: "field",
                            name: fieldName,
                            sortable,
                            string,
                            widget,
                        };
                    });
                }
            }
        });
        return {
            activeActions,
            columns: fieldParser.getFields(),
            relations: fieldParser.getRelations(),
        };
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
            relations: this.archInfo.relations,
            activeFields: this.archInfo.columns.map((col) => col.name),
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
        const resIds = this.model.root.data.map((datapoint) => datapoint.resId);
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
ListView.props = { ...standardViewProps };

ListView.template = `web.ListView`;
ListView.buttonTemplate = "web.ListView.Buttons";

registry.category("views").add("list", ListView);
