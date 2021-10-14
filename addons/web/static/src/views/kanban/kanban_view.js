/** @odoo-module **/

import { registry } from "@web/core/registry";
import { combineAttributes, XMLParser } from "@web/core/utils/xml";
import { useModel } from "@web/views/helpers/model";
import { useSetupView } from "@web/views/helpers/view_hook";
import { FieldParser } from "@web/views/helpers/view_utils";
import { KanbanModel } from "@web/views/kanban/kanban_model";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { Layout } from "@web/views/layout";
import { useViewButtons } from "@web/views/view_button/hook";

const KANBAN_BOX_ATTRIBUTE = "kanban-box";
const ACTION_TYPES = ["action", "object"];
const SPECIAL_TYPES = [...ACTION_TYPES, "edit", "open", "delete", "url", "set_cover"];
const TRANSPILED_EXPRESSIONS = [
    // Action names
    { regex: /\bwidget.editable\b/g, value: "props.info.activeActions.edit" },
    { regex: /\bwidget.deletable\b/g, value: "props.info.activeActions.delete" },
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
        kanbanBox.setAttribute("t-on-click", "onCardClicked(record)");
    }
    combineAttributes(kanbanBox, "class", "o_kanban_record");
    return kanbanBox;
};

const extractAttributes = (node, attributes) => {
    const attrs = Object.create(null);
    for (const rawAttr of attributes) {
        const attr = rawAttr.replace(/-[a-z]/gi, (_, c) => c.toUpperCase());
        attrs[attr] = node.getAttribute(rawAttr) || "";
        node.removeAttribute(rawAttr);
    }
    return attrs;
};

export class KanbanArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const className = xmlDoc.getAttribute("class") || null;
        const defaultGroupBy = xmlDoc.getAttribute("default_group_by");
        const activeActions = this.getActiveActions(xmlDoc);
        const quickCreate =
            activeActions.create &&
            this.isAttr(xmlDoc, "quick_create").truthy(true) &&
            this.isAttr(xmlDoc, "on_create").equalTo("quick_create");
        const fieldParser = new FieldParser(fields, "kanban");
        const tooltips = {};
        let kanbanBoxTemplate = document.createElement("t");
        let colorField = "color";

        const lookForTooltip = (field, options) => {
            const tooltipFields = options.group_by_tooltip;
            if (tooltipFields) {
                fieldParser.addRelation(
                    field.relation,
                    "display_name",
                    ...Object.keys(tooltipFields)
                );
                Object.assign(tooltips, tooltipFields);
            }
        };

        // Root level of the template
        this.visitXML(xmlDoc, (node) => {
            if (node.getAttribute("t-name") === KANBAN_BOX_ATTRIBUTE) {
                kanbanBoxTemplate = node;
                return;
            }
            // Case: field node
            if (node.tagName === "field") {
                const { field, name, options } = fieldParser.addField(node);
                lookForTooltip(field, options);
                if (!fieldParser.getWidget(name)) {
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
            // Converts server qweb attributes to Owl attributes.
            for (const { name, value } of node.attributes) {
                node.setAttribute(name, translateAttribute(value));
            }
        });

        // Concrete kanban box element in the template
        const kanbanBox =
            [...kanbanBoxTemplate.children].find((node) => node.tagName === "div") ||
            kanbanBoxTemplate;

        // Generates dropdown element
        const dropdown = document.createElement("t");
        const togglerClass = [];
        const menuClass = [];
        const transfers = [];
        let dropdownInserted = false;
        dropdown.setAttribute("t-component", "Dropdown");

        // Dropdown element
        for (const el of kanbanBox.querySelectorAll(".dropdown")) {
            const classes = el
                .getAttribute("class")
                .split(/\s+/)
                .filter((cls) => cls && cls !== "dropdown");
            combineAttributes(dropdown, "class", classes);
            if (!dropdownInserted) {
                transfers.push(() => el.replaceWith(dropdown));
                dropdownInserted = true;
            }
        }

        // Dropdown menu content
        for (const el of kanbanBox.querySelectorAll(".dropdown-menu")) {
            menuClass.push(el.getAttribute("class"));
            dropdown.append(...el.children);
            if (dropdownInserted) {
                transfers.push(() => el.remove());
            } else {
                transfers.push(() => el.replaceWith(dropdown));
                dropdownInserted = true;
            }
        }

        // Dropdown toggler content
        for (const el of kanbanBox.querySelectorAll(
            ".dropdown-toggle,.o_kanban_manage_toggle_button"
        )) {
            togglerClass.push(el.getAttribute("class"));
            const togglerSlot = document.createElement("t");
            togglerSlot.setAttribute("t-set-slot", "toggler");
            togglerSlot.append(...el.children);
            dropdown.appendChild(togglerSlot);
            if (dropdownInserted) {
                transfers.push(() => el.remove());
            } else {
                transfers.push(() => el.replaceWith(dropdown));
                dropdownInserted = true;
            }
        }

        transfers.forEach((transfer) => transfer());

        // Color picker
        for (const el of kanbanBox.querySelectorAll(".oe_kanban_colorpicker")) {
            const field = el.getAttribute("data-field");
            if (field) {
                colorField = field;
            }
            const colorPickerCaller = document.createElement("t");
            colorPickerCaller.setAttribute("t-call", "web.KanbanColorPicker");
            el.replaceWith(colorPickerCaller);
        }

        // Special actions
        for (const el of kanbanBox.querySelectorAll("a[type],button[type]")) {
            const { type } = extractAttributes(el, ["type"]);
            const params = { type };
            if (SPECIAL_TYPES.includes(type)) {
                if (ACTION_TYPES.includes(type)) {
                    Object.assign(params, extractAttributes(el, ["name", "confirm"]));
                } else if (type === "set_cover") {
                    const { field: fieldName, "auto-open": autoOpen } = extractAttributes(el, [
                        "field",
                        "auto-open",
                    ]);
                    const widget = fieldParser.getWidget(fieldName);
                    Object.assign(params, { fieldName, widget, autoOpen });
                }
                combineAttributes(el, "class", "oe_kanban_action");
                const strParams = Object.keys(params)
                    .map((k) => `${k}:"${params[k]}"`)
                    .join(",");
                el.setAttribute("t-on-click", `triggerAction(record,{${strParams}})`);
            }
        }

        dropdown.setAttribute("menuClass", `'${menuClass.join(" ")}'`);
        dropdown.setAttribute("togglerClass", `'${togglerClass.join(" ")}'`);

        return {
            arch,
            activeActions,
            className,
            defaultGroupBy,
            colorField,
            quickCreate,
            xmlDoc: applyDefaultAttributes(kanbanBox),
            fields: fieldParser.getFields(),
            tooltips,
            relations: fieldParser.getRelations(),
        };
    }
}

// -----------------------------------------------------------------------------

class KanbanView extends owl.Component {
    setup() {
        this.archInfo = new KanbanArchParser().parse(this.props.arch, this.props.fields);
        const { resModel, fields } = this.props;
        const { fields: activeFields, relations, defaultGroupBy } = this.archInfo;
        this.model = useModel(KanbanModel, {
            activeFields,
            fields,
            relations,
            resModel,
            defaultGroupBy,
            viewMode: "kanban",
        });
        useViewButtons(this.model);
        useSetupView({
            /** TODO **/
        });
    }
}

KanbanView.type = "kanban";
KanbanView.display_name = "Kanban";
KanbanView.icon = "fa-th-large";
KanbanView.multiRecord = true;
KanbanView.template = `web.KanbanView`;
KanbanView.components = { Layout, KanbanRenderer };

registry.category("views").add("kanban", KanbanView);
