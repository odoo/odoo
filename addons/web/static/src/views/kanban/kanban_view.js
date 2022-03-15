/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { combineAttributes, isTruthy, makeEl, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";
import { usePager } from "@web/search/pager_hook";
import { useModel } from "@web/views/helpers/model";
import { standardViewProps } from "@web/views/helpers/standard_view_props";
import { useSetupView } from "@web/views/helpers/view_hook";
import { getActiveActions } from "@web/views/helpers/view_utils";
import { KanbanModel } from "@web/views/kanban/kanban_model";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { Layout } from "@web/search/layout";
import { ViewNotFoundError } from "@web/views/view";
import { useViewButtons } from "@web/views/view_button/hook";

const { Component } = owl;

const KANBAN_BOX_ATTRIBUTE = "kanban-box";
const ACTION_TYPES = ["action", "object"];
const SPECIAL_TYPES = [...ACTION_TYPES, "edit", "open", "delete", "url", "set_cover"];
const TRANSPILED_EXPRESSIONS = [
    // Action names
    { regex: /\bwidget.editable\b/g, value: "canEditRecord()" },
    { regex: /\bwidget.deletable\b/g, value: "canDeleteRecord()" },
    // Special case: 'isHtmlEmpty' method
    { regex: /\bwidget.isHtmlEmpty\b/g, value: "isHtmlEmpty" },
    // `widget.prop` => `props.prop`
    { regex: /\bwidget\.(\w+)\b/g, value: "props.$1" },
    // `#{expr}` => `{{expr}}`
    { regex: /#{([^}]+)}/g, value: "{{$1}}" },
    // `kanban_image(model, field, idOrIds[, placeholder])` => `imageSrcFromRecordInfo(recordInfo, record)`
    {
        regex: /kanban_image\(([^)]*)\)/g,
        value: (_match, group) => {
            const args = group.split(",");
            return `imageSrcFromRecordInfo({
                model: ${args[0]},
                field: ${args[1]},
                idOrIds: ${args[2]},
                placeholder: ${args[3]},
            }, record)`;
        },
    },
    // `kanban_color(value)` => `getColorClass(record)`
    { regex: /\bkanban_color\(([^)]*)\)/g, value: `getColorClass($1)` },
    // `kanban_getcolor(value)` => `getColor(record)`
    { regex: /\bkanban_getcolor\(([^)]*)\)/g, value: `getColorIndex($1)` },
    // `record.prop.value` => `getValue(record,'prop')`
    { regex: /\brecord\.(\w+)\.value\b/g, value: `getValue(record, '$1')` },
    // `record.prop.raw_value` => `getRawValue(record,'prop')`
    { regex: /\brecord\.(\w+)\.raw_value\b/g, value: `getRawValue(record, '$1')` },
    // `record.prop` => `record.data.prop`
    { regex: /\brecord\.(\w+)\b/g, value: `record.data.$1` },
];
// These classes determine whether a click on a record should open it.
const KANBAN_CLICK_CLASSES = ["oe_kanban_global_click", "oe_kanban_global_click_edit"];

const isValidBox = (node) => node.tagName !== "t" || node.hasAttribute("t-component");

const hasClass = (node, ...classes) => {
    const classAttribute = node.getAttribute("class") || "";
    const attfClassAttribute = node.getAttribute("t-attf-class") || "";
    const nodeClasses = [
        ...classAttribute.split(/\s+/),
        ...attfClassAttribute.replace(/{{[^}]+}}/g, "").split(/\s+/),
    ];
    return classes.some((cls) => nodeClasses.includes(cls));
};

const applyDefaultAttributes = (kanbanBox) => {
    kanbanBox.setAttribute("t-att-tabindex", "isSample ? -1 : 0");
    kanbanBox.setAttribute("role", "article");
    kanbanBox.setAttribute("t-att-class", "getRecordClasses(record,groupOrRecord.group)");
    kanbanBox.setAttribute("t-att-data-id", "canResequenceRecords and record.id");
    if (hasClass(kanbanBox, ...KANBAN_CLICK_CLASSES)) {
        kanbanBox.setAttribute("t-on-click", "(ev) => this.onRecordClick(record, ev)");
    }
    return kanbanBox;
};

const extractAttributes = (node, attributes) => {
    const attrs = Object.create(null);
    for (const attr of attributes) {
        attrs[attr] = node.getAttribute(attr) || "";
        node.removeAttribute(attr);
    }
    return attrs;
};

export class KanbanArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const className = xmlDoc.getAttribute("class") || null;
        const defaultGroupBy = xmlDoc.getAttribute("default_group_by");
        const limit = xmlDoc.getAttribute("limit");
        const recordsDraggable = isTruthy(xmlDoc.getAttribute("records_draggable"), true);
        const activeActions = {
            ...getActiveActions(xmlDoc),
            groupArchive: isTruthy(xmlDoc.getAttribute("archivable"), true),
            groupCreate: isTruthy(xmlDoc.getAttribute("group_create"), true),
            groupDelete: isTruthy(xmlDoc.getAttribute("group_delete"), true),
            groupEdit: isTruthy(xmlDoc.getAttribute("group_edit"), true),
        };
        const onCreate =
            activeActions.create &&
            isTruthy(xmlDoc.getAttribute("quick_create"), true) &&
            (xmlDoc.getAttribute("on_create") || "quick_create");
        const quickCreateView = xmlDoc.getAttribute("quick_create_view");
        const tooltips = {};
        let kanbanBoxTemplate = makeEl("<t />");
        let colorField = "color";
        let cardColorField = null;
        let hasHandleWidget = null;
        const activeFields = {};

        // Root level of the template
        this.visitXML(xmlDoc, (node) => {
            if (node.getAttribute("t-name") === KANBAN_BOX_ATTRIBUTE) {
                node.removeAttribute("t-name");
                kanbanBoxTemplate = node;
                return;
            }
            // Case: field node
            if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, fields, "kanban");
                const name = fieldInfo.name;
                activeFields[name] = fieldInfo;
                Object.assign(tooltips, fieldInfo.options.group_by_tooltip);
                if (!fieldInfo.widget) {
                    // Fields without a specified widget are rendered as simple
                    // spans in kanban records.
                    const value = `record.data['${name}']`;
                    const tesc = makeEl(
                        `<span t-esc="(Array.isArray(${value}) ? ${value}[1] : ${value}) or ''"/>`
                    );
                    node.replaceWith(tesc);
                } else if (fieldInfo.widget === "handle") {
                    hasHandleWidget = true;
                }
            }
            // Converts server qweb attributes to Owl attributes.
            for (let { name, value: attrValue } of node.attributes) {
                for (const { regex, value } of TRANSPILED_EXPRESSIONS) {
                    attrValue = attrValue.replace(regex, value);
                }
                node.setAttribute(name, attrValue);
            }
            // Keep track of last update so images can be reloaded when they may have changed.
            if (node.tagName === "img") {
                const attSrc = node.getAttribute("t-att-src");
                if (
                    attSrc &&
                    attSrc.includes("imageSrcFromRecordInfo") &&
                    !activeFields.__last_update
                ) {
                    activeFields.__last_update = { type: "datetime" };
                }
            }
        });

        // Concrete kanban box element in the template
        let kanbanBox = kanbanBoxTemplate;
        while (!isValidBox(kanbanBox)) {
            const validChildren = [...kanbanBox.children].filter(isValidBox);
            if (validChildren.length !== 1) {
                throw new Error(
                    `Expected a single element to generate the kanban card template, got ${validChildren.length}.`
                );
            }
            kanbanBox = validChildren[0];
        }

        // Generates dropdown element
        const dropdown = makeEl(`<t t-component="'Dropdown'" position="'bottom-end'" />`);
        const togglerClass = [];
        const menuClass = [];
        const transfers = [];
        let progressAttributes = false;
        let dropdownInserted = false;

        // Progressbar
        for (const el of xmlDoc.getElementsByTagName("progressbar")) {
            const attrs = extractAttributes(el, ["field", "colors", "sum_field", "help"]);
            progressAttributes = {
                fieldName: attrs.field,
                colors: JSON.parse(attrs.colors),
                sumField: fields[attrs.sum_field] || false,
                help: attrs.help,
            };
        }

        // Dropdown element
        for (const el of kanbanBox.getElementsByClassName("dropdown")) {
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
        for (const el of kanbanBox.getElementsByClassName("dropdown-menu")) {
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
            const togglerSlot = makeEl(`<t t-set-slot="toggler" />`);
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

        // Color and color picker
        const { color } = extractAttributes(kanbanBox, ["color"]);
        if (color) {
            cardColorField = color;
        }
        for (const el of kanbanBox.getElementsByClassName("oe_kanban_colorpicker")) {
            const field = el.getAttribute("data-field");
            if (field) {
                colorField = field;
            }
            el.replaceWith(makeEl(`<t t-call="web.KanbanColorPicker" />`));
        }

        // Special actions
        for (const el of kanbanBox.querySelectorAll("a[type],button[type]")) {
            const type = el.getAttribute("type");
            if (ACTION_TYPES.includes(type)) {
                // action buttons are debounced in kanban records
                el.setAttribute("debounce", 300);
                // Action buttons will be compiled in compileButton, no further
                // processing is needed here
                continue;
            } else if (SPECIAL_TYPES.includes(type)) {
                el.removeAttribute("type");
                const params = { type };
                if (type === "set_cover") {
                    const { "data-field": fieldName, "auto-open": autoOpen } = extractAttributes(
                        el,
                        ["data-field", "auto-open"]
                    );
                    const widget = activeFields[fieldName].widget;
                    Object.assign(params, { fieldName, widget, autoOpen });
                }
                combineAttributes(el, "class", "oe_kanban_action");
                const strParams = Object.keys(params)
                    .map((k) => `${k}:"${params[k]}"`)
                    .join(",");
                el.setAttribute(
                    "t-on-click",
                    `() => this.triggerAction(record,group,{${strParams}})`
                );
            }
        }

        dropdown.setAttribute("menuClass", `'${menuClass.join(" ")}'`);
        dropdown.setAttribute("togglerClass", `'${togglerClass.join(" ")}'`);

        return {
            arch,
            activeActions,
            className,
            defaultGroupBy,
            hasHandleWidget,
            colorField,
            onCreate,
            quickCreateView,
            recordsDraggable,
            limit: limit && parseInt(limit, 10),
            progressAttributes,
            cardColorField,
            xmlDoc: applyDefaultAttributes(kanbanBox),
            fields: activeFields,
            tooltips,
            examples: xmlDoc.getAttribute("examples"),
        };
    }
}

// -----------------------------------------------------------------------------

export class KanbanView extends Component {
    setup() {
        this.actionService = useService("action");
        this.archInfo = new KanbanArchParser().parse(this.props.arch, this.props.fields);
        const { resModel, fields } = this.props;
        const { fields: activeFields, defaultGroupBy, onCreate, quickCreateView } = this.archInfo;
        this.model = useModel(KanbanModel, {
            activeFields,
            progressAttributes: this.archInfo.progressAttributes,
            fields,
            resModel,
            limit: this.archInfo.limit || this.props.limit,
            onCreate,
            quickCreateView,
            defaultGroupBy: this.props.searchMenuTypes.includes("groupBy") && defaultGroupBy,
            viewMode: "kanban",
            openGroupsByDefault: true,
        });
        useViewButtons(this.model);
        useSetupView({
            /** TODO **/
        });
        usePager(() => {
            if (!this.model.root.isGrouped) {
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
            }
        });
    }

    async openRecord(record) {
        const resIds = this.model.root.records.map((datapoint) => datapoint.resId);
        try {
            await this.actionService.switchView("form", { resId: record.resId, resIds });
        } catch (e) {
            if (e instanceof ViewNotFoundError) {
                // there's no form view in the current action
                return;
            }
            throw e;
        }
    }

    async createRecord(group) {
        const { onCreate } = this.archInfo;
        const { root } = this.model;
        if (root.canQuickCreate()) {
            await root.quickCreate(group);
        } else if (onCreate && onCreate !== "quick_create") {
            await this.actionService.doAction(onCreate, { additionalContext: root.context });
        } else {
            try {
                await this.actionService.switchView("form", { resId: false });
            } catch (e) {
                if (e instanceof ViewNotFoundError) {
                    // there's no form view in the current action
                    return;
                }
                throw e;
            }
        }
    }
}

KanbanView.type = "kanban";
KanbanView.display_name = "Kanban";
KanbanView.icon = "oi-align--vertical-top";
KanbanView.multiRecord = true;
KanbanView.template = `web.KanbanView`;
KanbanView.components = { Layout, KanbanRenderer };
KanbanView.props = { ...standardViewProps };
KanbanView.buttonTemplate = "web.KanbanView.Buttons";
KanbanView.ArchParser = KanbanArchParser;

registry.category("views").add("kanban", KanbanView);
