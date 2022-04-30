/** @odoo-module */

import { isFalsy, isTruthy, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";
import { archParseBoolean } from "@web/views/helpers/utils";
import { getActiveActions, getDecoration, processButton } from "../helpers/view_utils";
import { stringToOrderBy } from "../relational_model";

export class GroupListArchParser extends XMLParser {
    parse(arch, fields, jsClass) {
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
                const fieldInfo = Field.parseFieldNode(node, fields, "list", jsClass);
                activeFields[fieldInfo.name] = fieldInfo;
            }
        });
        return { activeFields, buttons };
    }
}

export class ListArchParser extends XMLParser {
    parse(arch, fields) {
        const xmlDoc = this.parseXML(arch);
        const activeActions = {
            ...getActiveActions(xmlDoc),
            exportXlsx: isTruthy(xmlDoc.getAttribute("export_xlsx"), true),
        };
        const decorations = getDecoration(xmlDoc);
        const editable = activeActions.edit ? xmlDoc.getAttribute("editable") : false;
        let defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order") || null);
        const expand = xmlDoc.getAttribute("expand") === "1";
        const activeFields = {};
        const columns = [];
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
        const jsClass = xmlDoc.getAttribute("js_class");

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
                        id: `column_${nextId++}`,
                        type: "button_group",
                        buttons: [button],
                        hasLabel: false,
                    };
                    columns.push(buttonGroup);
                }
            } else if (node.tagName === "field") {
                const fieldInfo = Field.parseFieldNode(node, fields, "list", jsClass);
                activeFields[fieldInfo.name] = fieldInfo;
                if (fieldInfo.widget === "handle") {
                    handleField = fieldInfo.name;
                }
                if (isFalsy(node.getAttribute("invisible"), true)) {
                    const displayName = fieldInfo.FieldComponent.displayName;
                    columns.push({
                        ...fieldInfo,
                        id: `column_${nextId++}`,
                        optional: node.getAttribute("optional") || false,
                        type: "field",
                        hasLabel: !(fieldInfo.attrs.nolabel || fieldInfo.FieldComponent.noLabel),
                        label:
                            (fieldInfo.widget && displayName && displayName.toString()) ||
                            fieldInfo.string,
                    });
                }
            } else if (node.tagName === "groupby" && node.getAttribute("name")) {
                const fieldName = node.getAttribute("name");
                const xmlSerializer = new XMLSerializer();
                const groupByArch = xmlSerializer.serializeToString(node);
                const groupByFields = fields[fieldName].relatedFields;
                const groupByArchInfo = groupListArchParser.parse(
                    groupByArch,
                    groupByFields,
                    jsClass
                );
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    activeFields: groupByArchInfo.activeFields,
                    fields: groupByFields,
                };
                return false;
            } else if (node.tagName === "header") {
                // AAB: not sure we need to handle invisible="1" button as the usecase seems way
                // less relevant than for fields (so for buttons, relying on the modifiers logic
                // that applies later on could be enough, even if the value is always true)
                headerButtons = [...node.children]
                    .map((node) => ({
                        ...processButton(node),
                        type: "button",
                        id: buttonId++,
                    }))
                    .filter((button) => button.modifiers.invisible !== true);
                return false;
            } else if (node.tagName === "create") {
                creates.push({
                    context: node.getAttribute("context"),
                    description: node.getAttribute("string"),
                });
            } else if (node.tagName === "tree") {
                const limitAttr = node.getAttribute("limit");
                treeAttr.limit = limitAttr && parseInt(limitAttr, 10);
                const groupsLimitAttr = node.getAttribute("groups_limit");
                treeAttr.groupsLimit = groupsLimitAttr && parseInt(groupsLimitAttr, 10);
                const noOpenAttr = node.getAttribute("no_open");
                treeAttr.noOpen = noOpenAttr && archParseBoolean(noOpenAttr);
            }
        });

        if (!defaultOrder.length && handleField) {
            defaultOrder = stringToOrderBy(handleField);
        }

        return {
            activeActions,
            creates,
            editable,
            expand,
            handleField,
            headerButtons,
            activeFields,
            columns,
            groupBy,
            defaultOrder,
            decorations,
            __rawArch: arch,
            ...treeAttr,
        };
    }
}
