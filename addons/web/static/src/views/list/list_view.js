/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { XMLParser } from "@web/core/utils/xml";
import { useModel } from "@web/views/helpers/model";
import { useSetupView } from "@web/views/helpers/view_hook";
import { FieldParser } from "@web/views/helpers/view_utils";
import { Layout } from "@web/views/layout";
import { ListRenderer } from "@web/views/list/list_renderer";
import { RelationalModel } from "@web/views/relational_model";

export class ListArchParser extends XMLParser {
    parse(arch, fields) {
        const fieldParser = new FieldParser(fields, "list");
        this.visitXML(arch, (node) => {
            if (node.tagName === "field") {
                if (
                    this.isAttr(node, "invisible").falsy() &&
                    this.isAttr(node, "optional").notEqualTo("hide")
                ) {
                    fieldParser.addField(node, (fieldName) => {
                        const string = node.getAttribute("string") || fields[fieldName].string;
                        const widget = node.getAttribute("widget") || null;
                        return {
                            type: "field",
                            name: fieldName,
                            string,
                            widget,
                        };
                    });
                }
            }
        });
        return {
            columns: fieldParser.getFields(),
            relations: fieldParser.getRelations(),
        };
    }
}

// -----------------------------------------------------------------------------

class ListView extends owl.Component {
    setup() {
        this.actionService = useService("action");
        this.archInfo = new ListArchParser().parse(this.props.arch, this.props.fields);
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            fields: this.props.fields,
            relations: this.archInfo.relations,
            activeFields: this.archInfo.columns.map((col) => col.name),
            viewMode: "list",
        });

        this.openRecord = this.openRecord.bind(this);

        useSetupView({
            /** TODO **/
        });
    }

    openRecord(record) {
        const resIds = this.model.root.data.map((datapoint) => datapoint.resId);
        this.actionService.switchView("form", { resId: record.resId, resIds });
    }
}

ListView.type = "list";
ListView.display_name = "List";
ListView.icon = "fa-list-ul";
ListView.multiRecord = true;
ListView.template = `web.ListView`;
ListView.components = { Layout, ListRenderer };

registry.category("views").add("list", ListView);
