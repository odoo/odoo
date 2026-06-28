import { exprToBoolean } from "@web/core/utils/strings";
import { visitXML } from "@web/core/utils/xml";
import { combineModifiers } from "@web/model/relational_model/utils";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { Field } from "@web/views/fields/field";
import { getActiveActions, getDecoration, processButton } from "@web/views/utils";
import { encodeObjectForTemplate } from "@web/views/view_compiler";
import { Widget } from "@web/views/widgets/widget";

export class GroupListArchParser {
    parse(arch, models, modelName, jsClass) {
        const fieldNodes = {};
        const fieldNextIds = {};
        const buttons = [];
        let buttonId = 0;
        visitXML(arch, (node) => {
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
        return { fieldNodes, buttons };
    }
}

export class ListArchParser {
    parseFieldNode(node, models, modelName, fieldNextIds, fieldNodes) {
        const fieldInfo = Field.parseFieldNode(node, models, modelName, "list");
        if (!(fieldInfo.name in fieldNextIds)) {
            fieldNextIds[fieldInfo.name] = 0;
        }
        const fieldId = `${fieldInfo.name}_${fieldNextIds[fieldInfo.name]++}`;
        fieldNodes[fieldId] = fieldInfo;
        node.setAttribute("field_id", fieldId);
        const label = fieldInfo.field.label;
        return {
            ...fieldInfo,
            className: node.getAttribute("class"),
            optional: node.getAttribute("optional") || false,
            type: "field",
            fieldType: fieldInfo.type,
            label: (fieldInfo.widget && label && label.toString()) || fieldInfo.string,
        };
    }

    parseWidgetNode(node, models, modelName) {
        return Widget.parseWidgetNode(node);
    }

    processButton(node) {
        return processButton(node);
    }

    parse(xmlDoc, models, modelName) {
        const fieldNodes = {};
        const widgetNodes = {};
        let widgetNextId = 0;
        const columns = [];
        const fields = models[modelName].fields;
        let buttonId = 0;
        const groupBy = {
            buttons: {},
            fields: {},
        };
        let headerButtons = [];
        const controls = [];
        const groupListArchParser = new GroupListArchParser();
        let buttonGroup;
        let handleField = null;
        const treeAttr = {};
        let nextId = 0;
        const fieldNextIds = {};
        visitXML(xmlDoc, (node) => {
            if (node.tagName !== "button") {
                buttonGroup = undefined;
            }
            if (node.tagName === "button") {
                const button = {
                    ...this.processButton(node),
                    defaultRank: "btn-link",
                    type: "button",
                    id: buttonId++,
                };
                const width = button.attrs.width;
                if (buttonGroup && !width) {
                    buttonGroup.buttons.push(button);
                    buttonGroup.column_invisible = combineModifiers(
                        buttonGroup.column_invisible,
                        node.getAttribute("column_invisible"),
                        "AND"
                    );
                } else {
                    buttonGroup = {
                        id: `column_${nextId++}`,
                        type: "button_group",
                        buttons: [button],
                        hasLabel: false,
                        column_invisible: node.getAttribute("column_invisible"),
                    };
                    columns.push(buttonGroup);
                    if (width) {
                        buttonGroup.attrs = { width };
                        buttonGroup = undefined;
                    }
                }
            } else if (node.tagName === "field") {
                const fieldDescriptor = this.parseFieldNode(
                    node,
                    models,
                    modelName,
                    fieldNextIds,
                    fieldNodes
                );
                if (fieldDescriptor.isHandle) {
                    handleField = fieldDescriptor.name;
                }
                columns.push({
                    ...fieldDescriptor,
                    id: `column_${nextId++}`,
                    hasLabel: !(
                        fieldDescriptor.field.label === false ||
                        exprToBoolean(fieldDescriptor.attrs.nolabel) === true
                    ),
                });
                return false;
            } else if (node.tagName === "widget") {
                const widgetInfo = this.parseWidgetNode(node);
                const widgetId = `widget_${++widgetNextId}`;
                widgetNodes[widgetId] = widgetInfo;
                node.setAttribute("widget_id", widgetId);

                const widgetProps = {
                    name: widgetInfo.name,
                    // FIXME: this is dumb, we encode it into a weird object so that the widget
                    // can decode it later...
                    node: encodeObjectForTemplate({ attrs: widgetInfo.attrs }).slice(1, -1),
                    className: node.getAttribute("class") || "",
                    widgetInfo,
                };
                columns.push({
                    ...widgetInfo,
                    props: widgetProps,
                    id: `column_${nextId++}`,
                    type: "widget",
                });
            } else if (node.tagName === "column") {
                const columnFields = [];
                for (const child of node.children) {
                    if (child.tagName === "field") {
                        const fieldDescriptor = this.parseFieldNode(
                            child,
                            models,
                            modelName,
                            fieldNextIds,
                            fieldNodes
                        );
                        columnFields.push({
                            ...fieldDescriptor,
                            id: `field_${nextId++}`,
                            hasLabel: false,
                        });
                    }
                }
                const labelAttr = node.getAttribute("string");
                const widthAttr = node.getAttribute("width");
                columns.push({
                    id: `column_${nextId++}`,
                    type: "column_group",
                    label: labelAttr !== null ? labelAttr : columnFields[0].label,
                    hasLabel: true,
                    optional: false,
                    column_invisible: node.getAttribute("column_invisible"),
                    fields: columnFields,
                    ...(widthAttr ? { attrs: { width: widthAttr } } : {}),
                });
                return false;
            } else if (node.tagName === "groupby" && node.getAttribute("name")) {
                const fieldName = node.getAttribute("name");
                const coModelName = fields[fieldName].relation;
                const groupByArchInfo = groupListArchParser.parse(node, models, coModelName);
                groupBy.buttons[fieldName] = groupByArchInfo.buttons;
                groupBy.fields[fieldName] = {
                    fieldNodes: groupByArchInfo.fieldNodes,
                    fields: models[coModelName].fields,
                };
                return false;
            } else if (node.tagName === "header") {
                headerButtons = [...node.children].map((node) => ({
                    ...this.processButton(node),
                    type: "button",
                    id: buttonId++,
                }));
                return false;
            } else if (node.tagName === "control") {
                for (const childNode of node.children) {
                    if (childNode.tagName === "button") {
                        controls.push({
                            type: "button",
                            ...processButton(childNode),
                        });
                    } else if (childNode.tagName === "create") {
                        controls.push({
                            type: "create",
                            name: childNode.getAttribute("name"),
                            context: childNode.getAttribute("context"),
                            string: childNode.getAttribute("string"),
                            invisible: childNode.getAttribute("invisible"),
                            hotkey: childNode.getAttribute("data-hotkey"),
                        });
                    } else if (childNode.tagName === "delete") {
                        controls.push({
                            type: "delete",
                            invisible: childNode.getAttribute("invisible"),
                        });
                    }
                }
                return false;
            } else if ("list" === node.tagName) {
                const activeActions = {
                    ...getActiveActions(xmlDoc),
                    exportXlsx: exprToBoolean(xmlDoc.getAttribute("export_xlsx"), true),
                    createGroup: exprToBoolean(xmlDoc.getAttribute("group_create"), true),
                    editGroup: exprToBoolean(xmlDoc.getAttribute("group_edit"), true),
                    deleteGroup: exprToBoolean(xmlDoc.getAttribute("group_delete"), true),
                };
                treeAttr.activeActions = activeActions;

                treeAttr.className = xmlDoc.getAttribute("class") || null;
                treeAttr.editable = xmlDoc.getAttribute("editable");
                treeAttr.multiEdit = activeActions.edit
                    ? exprToBoolean(node.getAttribute("multi_edit") || "")
                    : false;

                treeAttr.openFormView = treeAttr.editable
                    ? exprToBoolean(xmlDoc.getAttribute("open_form_view") || "")
                    : false;
                treeAttr.defaultGroupBy = xmlDoc.hasAttribute("default_group_by")
                    ? xmlDoc.getAttribute("default_group_by").split(",")
                    : null;

                const limitAttr = node.getAttribute("limit");
                treeAttr.limit = limitAttr && parseInt(limitAttr, 10);

                const countLimitAttr = node.getAttribute("count_limit");
                treeAttr.countLimit = countLimitAttr && parseInt(countLimitAttr, 10);

                const groupsLimitAttr = node.getAttribute("groups_limit");
                treeAttr.groupsLimit = groupsLimitAttr && parseInt(groupsLimitAttr, 10);

                treeAttr.noOpen = exprToBoolean(node.getAttribute("no_open") || "");
                treeAttr.rawExpand = xmlDoc.getAttribute("expand");
                treeAttr.decorations = getDecoration(xmlDoc);

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
            const handleFieldSort = `${handleField}, id`;
            treeAttr.defaultOrder = stringToOrderBy(handleFieldSort);
        }

        return {
            controls,
            headerButtons,
            fieldNodes,
            widgetNodes,
            columns,
            groupBy,
            xmlDoc,
            ...treeAttr,
        };
    }
}
