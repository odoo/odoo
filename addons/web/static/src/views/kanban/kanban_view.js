/* @odoo-module */

import { registry } from "@web/core/registry";
import { XMLParser } from "@web/core/utils/xml";
import { ControlPanel } from "@web/search/control_panel/control_panel";
import { useModel } from "@web/views/helpers/model";
import { useDebugMenu } from "../../core/debug/debug_menu";
import { RelationalModel } from "../relational_model";
import { KanbanRenderer } from "./kanban_renderer";

const KANBAN_BOX_ATTRIBUTE = "kanban-box";
const TRANSPILED_EXPRESSIONS = [
    // `widget.prop` => `props.prop`
    { regex: /\bwidget\.(\w+)\b/g, value: "props.$1" },
    // `record.prop` => `record.data.prop`
    { regex: /\brecord\.(\w+)\b/g, value: "record.data.$1" },
    // `prop.raw_value` => `prop`
    { regex: /(\w+)\.raw_value\b/g, value: "$1" },
    // `#{expr}` => `{{expr}}`
    { regex: /#{([^}]+)}/g, value: "{{$1}}" },
];

const translateAttribute = (attrValue) => {
    for (const { regex, value } of TRANSPILED_EXPRESSIONS) {
        attrValue = attrValue.replace(regex, value);
    }
    return attrValue;
};

const applyDefaultAttributes = (kanbanBox) => {
    const originalClass = kanbanBox.getAttribute("class");
    kanbanBox.setAttribute("t-on-click", "openRecord(record)");
    kanbanBox.setAttribute("class", `o_kanban_record ${originalClass}`);
    return kanbanBox;
};

class KanbanArchParser extends XMLParser {
    parse(arch) {
        const fields = new Set();
        const xmlDoc = this.parseXML(arch);
        const className = xmlDoc.getAttribute("class") || null;
        let kanbanBoxTemplate = document.createElement("t");

        // Root level of the template
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                fields.add(node.getAttribute("name"));
            }
            if (node.getAttribute("t-name") === KANBAN_BOX_ATTRIBUTE) {
                kanbanBoxTemplate = node;
            }
        });

        // Concrete kanban box element in the template
        const kanbanBox =
            [...kanbanBoxTemplate.children].find(
                (node) => node.tagName === "div"
            ) || kanbanBoxTemplate;

        // Kanban box template
        this.visitXML(kanbanBoxTemplate, (node) => {
            if (node.tagName === "field") {
                fields.add(node.getAttribute("name"));
            }
            // Converts server qweb attributes to Owl attributes.
            for (const { name, value } of node.attributes) {
                node.setAttribute(name, translateAttribute(value));
            }
        });

        return {
            fields: [...fields],
            arch,
            xmlDoc: applyDefaultAttributes(kanbanBox),
            className,
        };
    }
}

// -----------------------------------------------------------------------------

class KanbanView extends owl.Component {
    setup() {
        console.log(this.props);
        useDebugMenu("view", { component: this });
        this.archInfo = new KanbanArchParser().parse(
            this.props.arch,
            this.props.fields
        );
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            fields: this.props.fields,
            activeFields: this.archInfo.fields,
        });
    }
}

KanbanView.type = "kanban";
KanbanView.display_name = "Kanban";
KanbanView.icon = "fa-th-large";
KanbanView.multiRecord = true;
KanbanView.template = `web.KanbanView`;
KanbanView.components = { ControlPanel, KanbanRenderer };

registry.category("views").add("kanban", KanbanView);
