/** @odoo-module */

import { isFalsy, isTruthy, stringToOrderBy, XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/fields/field";
import { archParseBoolean } from "@web/views/helpers/utils";
import { getActiveActions, getDecoration, processButton } from "../helpers/view_utils";

export class GroupListArchParser extends XMLParser {
    parse(arch, models, modelName, jsClass) {
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
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "list", jsClass);
                activeFields[fieldInfo.name] = fieldInfo;
            }
        });
        return { activeFields, buttons };
    }
}

export class ListArchParser extends XMLParser {
    parse(arch, models, modelName) {
        const xmlDoc = this.parseXML(arch);
        const activeFields = {};
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
                const fieldInfo = Field.parseFieldNode(node, models, modelName, "list");
                activeFields[fieldInfo.name] = fieldInfo;
                if (fieldInfo.widget === "handle") {
                    handleField = fieldInfo.name;
                }
                if (isFalsy(node.getAttribute("invisible"), true)) {
                    const displayName = fieldInfo.FieldComponent.displayName;
                    columns.push({
                        ...fieldInfo,
                        id: `column_${nextId++}`,
                        className: node.getAttribute("class"), // for oe_edit_only and oe_read_only
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
                const coModelName = fields[fieldName].relation;
                const groupByArchInfo = groupListArchParser.parse(groupByArch, models, coModelName);
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    activeFields: groupByArchInfo.activeFields,
                    fields: models[coModelName],
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
            } else if (["tree", "list"].includes(node.tagName)) {
                const activeActions = {
                    ...getActiveActions(xmlDoc),
                    exportXlsx: isTruthy(xmlDoc.getAttribute("export_xlsx"), true),
                };
                treeAttr.activeActions = activeActions;

                treeAttr.editable = activeActions.edit ? xmlDoc.getAttribute("editable") : false;
                treeAttr.multiEdit = activeActions.edit
                    ? archParseBoolean(node.getAttribute("multi_edit") || "")
                    : false;

                const limitAttr = node.getAttribute("limit");
                treeAttr.limit = limitAttr && parseInt(limitAttr, 10);

                const groupsLimitAttr = node.getAttribute("groups_limit");
                treeAttr.groupsLimit = groupsLimitAttr && parseInt(groupsLimitAttr, 10);

                treeAttr.defaultOrder = stringToOrderBy(
                    xmlDoc.getAttribute("default_order") || null
                );
                treeAttr.noOpen = archParseBoolean(node.getAttribute("no_open") || "");
                treeAttr.expand = archParseBoolean(xmlDoc.getAttribute("expand") || "");
                treeAttr.decorations = getDecoration(xmlDoc);
            }
        });

        return {
            creates,
            handleField,
            headerButtons,
            activeFields,
            columns,
            groupBy,
            __rawArch: arch,
            ...treeAttr,
        };
    }
}
