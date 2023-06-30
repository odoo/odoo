/** @odoo-module */

import {
    addFieldDependencies,
    archParseBoolean,
    getActiveActions,
    getDecoration,
    processButton,
    stringToOrderBy,
} from "@web/views/utils";
import { Field } from "@web/views/fields/field";
import { XMLParser } from "@web/core/utils/xml";
import { Widget } from "@web/views/widgets/widget";
import { encodeObjectForTemplate } from "@web/views/view_compiler";

export class GroupListArchParser extends XMLParser {
    parse(arch, models, modelName, jsClass) {
        const fieldNodes = {};
        const fieldNextIds = {};
        const buttons = [];
        let buttonId = 0;
        this.visitXML(arch, (node) => {
            if (node.tagName === "button") {
                buttons.push({
                    ...processButton(node),
                    id: buttonId++,
                });
                return false;
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "list", jsClass);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                return false;
            }
        });
        const activeFields = {};
        for (const fieldNode of Object.values(fieldNodes)) {
            activeFields[fieldNode.name] = fieldNode;
        }
        return { fieldNodes, activeFields, buttons };
    }
}

export class ListArchParser extends XMLParser {
    isColumnVisible(columnInvisibleModifier) {
        return columnInvisibleModifier !== true;
    }

    parseFieldNode(node, models, modelName) {
        return Field.parseFieldNode(node, models, modelName, "list");
    }

    parseWidgetNode(node, models, modelName) {
        return Widget.parseWidgetNode(node);
    }

    processButton(node) {
        return processButton(node);
    }

    parse(arch, models, modelName) {
        const xmlDoc = this.parseXML(arch);
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const columns = [];
        const fields = models[modelName];
        let buttonId = 0;
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let headerButtons = [];
        const creates = [];
        const groupListArchParser = new GroupListArchParser();
        let buttonGroup;
        let handleField = null;
        const treeAttr = {};
        let nextId = 0;
        const activeFields = {};
        const fieldNextIds = {};
        this.visitXML(arch, (node) => {
            if (node.tagName !== "button") {
                buttonGroup = undefined;
            }
            if (node.tagName === "button") {
                const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
                if (this.isColumnVisible(modifiers.column_invisible)) {
                    const button = {
                        ...this.processButton(node),
                        defaultRank: "btn-link",
                        type: "button",
                        id: buttonId++,
                    };
                    if (buttonGroup) {
                        buttonGroup.buttons.push(button);
                    } else {
                        buttonGroup = {
                            id: `column_${nextId++}`,
                            type: "button_group",
                            buttons: [button],
                            hasLabel: false,
                        };
                        columns.push(buttonGroup);
                    }
                }
            } else if (node.tagName === "field") {
                const fieldInfo = this.parseFieldNode(node, models, modelName);
                if (!(fieldInfo.name in fieldNextIds)) {
                    fieldNextIds[fieldInfo.name] = 0;
                }
                const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
                fieldNodes[fieldId] = fieldInfo;
                node.setAttribute("field_id", fieldId);
                if (fieldInfo.widget === "handle") {
                    handleField = fieldInfo.name;
                }
                addFieldDependencies(fieldInfo, activeFields, models[modelName]);
                if (this.isColumnVisible(fieldInfo.modifiers.column_invisible)) {
                    const label = fieldInfo.field.label;
                    columns.push({
                        ...fieldInfo,
                        id: `column_${nextId++}`,
                        className: node.getAttribute("class"), // for oe_edit_only and oe_read_only
                        optional: node.getAttribute("optional") || false,
                        type: "field",
                        hasLabel: !(
                            archParseBoolean(fieldInfo.attrs.nolabel) || fieldInfo.field.noLabel
                        ),
                        label: (fieldInfo.widget && label && label.toString()) || fieldInfo.string,
                    });
                }
                return false;
            } else if (node.tagName === "widget") {
                const widgetInfo = this.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                node.setAttribute("widget_id", widgetId);
                addFieldDependencies(widgetInfo, activeFields, models[modelName]);

                const widgetProps = {
                    name: widgetInfo.name,
                    // FIXME: this is dumb, we encode it into a weird object so that the widget
                    // can decode it later...
                    node: encodeObjectForTemplate({ attrs: widgetInfo.attrs }).slice(1, -1),
                    className: node.getAttribute("class") || "",
                };
                columns.push({
                    ...widgetInfo,
                    props: widgetProps,
                    id: `column_${nextId++}`,
                    type: "widget",
                });
            } else if (node.tagName === "groupby" && node.getAttribute("name")) {
                const fieldName = node.getAttribute("name");
                const xmlSerializer = new XMLSerializer();
                const groupByArch = xmlSerializer.serializeToString(node);
                const coModelName = fields[fieldName].relation;
                const groupByArchInfo = groupListArchParser.parse(groupByArch, models, coModelName);
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    activeFields: groupByArchInfo.activeFields,
                    fieldNodes: groupByArchInfo.fieldNodes,
                    fields: models[coModelName],
                };
                return false;
            } else if (node.tagName === "header") {
                // AAB: not sure we need to handle invisible="1" button as the usecase seems way
                // less relevant than for fields (so for buttons, relying on the modifiers logic
                // that applies later on could be enough, even if the value is always true)
                headerButtons = [...node.children]
                    .map((node) => ({
                        ...this.processButton(node),
                        type: "button",
                        id: buttonId++,
                    }))
                    .filter((button) => button.modifiers.invisible !== true);
                return false;
            } else if (node.tagName === "control") {
                for (const childNode of node.children) {
                    if (childNode.tagName === "button") {
                        creates.push({
                            type: "button",
                            ...processButton(childNode),
                        });
                    } else if (childNode.tagName === "create") {
                        creates.push({
                            type: "create",
                            context: childNode.getAttribute("context"),
                            string: childNode.getAttribute("string"),
                        });
                    }
                }
                return false;
            } else if (["tree", "list"].includes(node.tagName)) {
                const activeActions = {
                    ...getActiveActions(xmlDoc),
                    exportXlsx: archParseBoolean(xmlDoc.getAttribute("export_xlsx"), true),
                };
                treeAttr.activeActions = activeActions;

                treeAttr.className = xmlDoc.getAttribute("class") || null;
                treeAttr.editable = xmlDoc.getAttribute("editable");
                treeAttr.multiEdit = activeActions.edit
                    ? archParseBoolean(node.getAttribute("multi_edit") || "")
                    : false;

                const limitAttr = node.getAttribute("limit");
                treeAttr.limit = limitAttr && parseInt(limitAttr, 10);

                const countLimitAttr = node.getAttribute("count_limit");
                treeAttr.countLimit = countLimitAttr && parseInt(countLimitAttr, 10);

                const groupsLimitAttr = node.getAttribute("groups_limit");
                treeAttr.groupsLimit = groupsLimitAttr && parseInt(groupsLimitAttr, 10);

                treeAttr.noOpen = archParseBoolean(node.getAttribute("no_open") || "");
                treeAttr.rawExpand = xmlDoc.getAttribute("expand");
                treeAttr.decorations = getDecoration(xmlDoc);

                treeAttr.defaultGroupBy = xmlDoc.getAttribute("default_group_by");
                treeAttr.defaultOrder = stringToOrderBy(
                    xmlDoc.getAttribute("default_order") || null
                );

                // custom open action when clicking on record row
                const action = xmlDoc.getAttribute("action");
                const type = xmlDoc.getAttribute("type");
                treeAttr.openAction = action && type ? { action, type } : null;
            }
        });

        if (!treeAttr.defaultOrder.length && handleField) {
            treeAttr.defaultOrder = stringToOrderBy(handleField);
        }

        for (const fieldNode of Object.values(fieldNodes)) {
            const fieldName = fieldNode.name;
            if (activeFields[fieldName]) {
                const { alwaysInvisible } = fieldNode;
                activeFields[fieldName] = {
                    ...fieldNode,
                    // a field can only be considered to be always invisible
                    // if all its nodes are always invisible
                    alwaysInvisible: activeFields[fieldName].alwaysInvisible && alwaysInvisible,
                };
            } else {
                activeFields[fieldName] = fieldNode;
            }
        }

        return {
            creates,
            handleField,
            headerButtons,
            fieldNodes,
            widgetNodes,
            activeFields,
            columns,
            groupBy,
            xmlDoc,
            __rawArch: arch,
            ...treeAttr,
        };
    }
}
