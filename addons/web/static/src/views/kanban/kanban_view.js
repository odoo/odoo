/** @odoo-module */

import { useDebugMenu } from "../../core/debug/debug_menu";
import { registry } from "../../core/registry";
import { combineAttributes, XMLParser } from "../../core/utils/xml";
import { ControlPanel } from "../../search/control_panel/control_panel";
import { useModel } from "../../views/helpers/model";
import { FieldParser } from "../helpers/view_utils";
import { RelationalModel } from "../relational_model";
import { KanbanRenderer } from "./kanban_renderer";

const KANBAN_BOX_ATTRIBUTE = "kanban-box";
const TRANSPILED_EXPRESSIONS = [
    // `widget.prop` => `props.prop`
    { regex: /\bwidget\.(\w+)\b/g, value: "props.$1" },
    // `record.prop` => `record.data.prop`
    { regex: /\brecord\.(\w+)\b/g, value: "record.data.$1" },
    // `prop.raw_value` => `prop`
    { regex: /(\w+)\.(raw_)?value\b/g, value: "$1" },
    // `#{expr}` => `{{expr}}`
    { regex: /#{([^}]+)}/g, value: "{{$1}}" },
];
// These classes determine whether a click on a record should open it.
const KANBAN_CLICK_CLASSES = ["oe_kanban_global_click", "oe_kanban_global_click_edit"];

const hasClass = (node, ...classes) => {
    const classAttribute = node.getAttribute("class") || "";
    const attfClassAttribute = node.getAttribute("t-attf-class") || "";
    const nodeClasses = [
        ...classAttribute.split(/\s+/),
        ...attfClassAttribute.replace(/{{[^}]+}}/g, "").split(/\s+/),
    ];
    return classes.some((cls) => nodeClasses.includes(cls));
};

const translateAttribute = (attrValue) => {
    for (const { regex, value } of TRANSPILED_EXPRESSIONS) {
        attrValue = attrValue.replace(regex, value);
    }
    return attrValue;
};

const applyDefaultAttributes = (kanbanBox) => {
    kanbanBox.setAttribute("tabindex", 0);
    kanbanBox.setAttribute("role", "article");
    if (hasClass(kanbanBox, ...KANBAN_CLICK_CLASSES)) {
        kanbanBox.setAttribute("t-on-click", "openRecord(record)");
    }
    combineAttributes(kanbanBox, "class", "o_kanban_record", " ");
    return kanbanBox;
};

class KanbanArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const className = xmlDoc.getAttribute("class") || null;
        const fieldParser = new FieldParser(fields);
        let kanbanBoxTemplate = document.createElement("t");

        // Root level of the template
        this.visitXML(xmlDoc, (node) => {
            if (node.tagName === "field") {
                fieldParser.addField(node);
            } else if (node.getAttribute("t-name") === KANBAN_BOX_ATTRIBUTE) {
                kanbanBoxTemplate = node;
            }
        });

        // Concrete kanban box element in the template
        const kanbanBox =
            [...kanbanBoxTemplate.children].find((node) => node.tagName === "div") ||
            kanbanBoxTemplate;

        // Kanban box template
        this.visitXML(kanbanBoxTemplate, (node) => {
            // Converts server qweb attributes to Owl attributes.
            for (const { name, value } of node.attributes) {
                node.setAttribute(name, translateAttribute(value));
            }
            // Fields
            if (node.tagName === "field") {
                const { name, widget } = fieldParser.addField(node);
                if (!widget) {
                    // Fields without a specified widget are rendered as simple
                    // spans in kanban records.
                    const tesc = document.createElement("span");
                    const value = `record.data['${name}']`;
                    tesc.setAttribute(
                        "t-esc",
                        `(Array.isArray(${value}) ? ${value}[1] : ${value}) or ''`
                    );
                    node.replaceWith(tesc);
                }
            }
            // Dropdowns
            if (hasClass(node, "dropdown")) {
                const dropdown = document.createElement("Dropdown");
                node.replaceWith(dropdown);
            }
        });

        return {
            arch,
            className,
            xmlDoc: applyDefaultAttributes(kanbanBox),
            fields: fieldParser.getFields(),
            relations: fieldParser.getRelations(),
        };
    }
}

// -----------------------------------------------------------------------------

class KanbanView extends owl.Component {
    setup() {
        useDebugMenu("view", { component: this });
        this.archInfo = new KanbanArchParser().parse(this.props.arch, this.props.fields);
        this.model = useModel(RelationalModel, {
            resModel: this.props.resModel,
            fields: this.props.fields,
            relations: this.archInfo.relations,
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
