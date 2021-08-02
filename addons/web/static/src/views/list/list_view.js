/** @odoo-module */

import { registry } from "@web/core/registry";
import { XMLParser } from "../../core/utils/xml";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useModel } from "@web/views/helpers/model";
import { useDebugMenu } from "../../core/debug/debug_menu";
import { FieldParser } from "../helpers/view_utils";
import { RelationalModel } from "../relational_model";
import { ListRenderer } from "./list_renderer";

class ListArchParser extends XMLParser {
    parse(arch, fields) {
        const fieldParser = new FieldParser(fields);
        this.visitXML(arch, (node) => {
            if (node.tagName === "field") {
                if (
                    this.isAttr(node, "invisible").falsy() &&
                    this.isAttr(node, "optional").notEqualTo("hide")
                ) {
                    fieldParser.addField(node, (fieldName) => {
                        const string = node.getAttribute("string") || fields[fieldName].string;
                        return {
                            type: "field",
                            name: fieldName,
                            string,
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
        console.log(this.props);
        useDebugMenu("view", { component: this });
        this.archInfo = new ListArchParser().parse(this.props.arch, this.props.fields);
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            fields: this.props.fields,
            relations: this.archInfo.relations,
            activeFields: this.archInfo.columns.map((col) => col.name),
        });
    }
}

ListView.type = "list";
ListView.display_name = "List";
ListView.icon = "fa-list-ul";
ListView.multiRecord = true;
ListView.template = `web.ListView`;
ListView.components = { ControlPanel, ListRenderer };

registry.category("views").add("list", ListView);
