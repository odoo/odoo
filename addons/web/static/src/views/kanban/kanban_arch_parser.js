import { exprToBoolean } from "@web/core/utils/strings";
import { extractAttributes } from "@web/core/utils/xml";
import { stringToOrderBy } from "@web/search/utils/order_by";
import { CardArchParser } from "@web/views/card/card_arch_parser";
import { processButton } from "@web/views/utils";

export class KanbanArchParser {
    parse(xmlDoc, models, modelName) {
        const cardArchInfo = new CardArchParser().parse(xmlDoc, models, modelName);

        const action = xmlDoc.getAttribute("action");
        const type = xmlDoc.getAttribute("type");
        const openAction = action && type ? { action, type } : null;

        const activeActions = {
            ...cardArchInfo.activeActions,
            archiveGroup: exprToBoolean(xmlDoc.getAttribute("archivable"), true),
            createGroup: exprToBoolean(xmlDoc.getAttribute("group_create"), true),
            deleteGroup: exprToBoolean(xmlDoc.getAttribute("group_delete"), true),
            editGroup: exprToBoolean(xmlDoc.getAttribute("group_edit"), true),
            quickCreate:
                cardArchInfo.activeActions.create &&
                exprToBoolean(xmlDoc.getAttribute("quick_create"), true),
        };

        const limit = xmlDoc.getAttribute("limit");
        const countLimit = xmlDoc.getAttribute("count_limit");

        const defaultGroupBy = xmlDoc.hasAttribute("default_group_by")
            ? xmlDoc.getAttribute("default_group_by").split(",")
            : null;

        const tooltipInfo = {};
        let handleField = null;
        for (const fieldNode of Object.values(cardArchInfo.fieldNodes)) {
            if (fieldNode.options.group_by_tooltip) {
                tooltipInfo[fieldNode.name] = fieldNode.options.group_by_tooltip;
            }
            if (fieldNode.isHandle) {
                handleField = fieldNode.name;
            }
        }

        let defaultOrder = stringToOrderBy(xmlDoc.getAttribute("default_order") || null);
        if (!defaultOrder.length && handleField) {
            const handleFieldSort = `${handleField}, id`;
            defaultOrder = stringToOrderBy(handleFieldSort);
        }

        const headerButtons = [];
        const controls = [];
        let nextButtonId = 0;
        let progressAttributes = false;
        for (const node of xmlDoc.children) {
            switch (node.tagName) {
                case "header": {
                    const buttons = [...node.children]
                        .filter((childNode) => childNode.tagName === "button")
                        .map((childNode) => ({
                            ...this.processButton(childNode),
                            type: "button",
                            id: nextButtonId++,
                        }));
                    headerButtons.push(...buttons);
                    break;
                }
                case "control": {
                    for (const childNode of node.children) {
                        if (childNode.tagName === "button") {
                            controls.push({
                                type: "button",
                                ...processButton(childNode),
                            });
                        } else if (childNode.tagName === "create") {
                            controls.push({
                                type: "create",
                                context: childNode.getAttribute("context"),
                                string: childNode.getAttribute("string"),
                                invisible: childNode.getAttribute("invisible"),
                                class: childNode.getAttribute("class"),
                            });
                        } else if (childNode.tagName === "delete") {
                            controls.push({
                                type: "delete",
                                invisible: childNode.getAttribute("invisible"),
                            });
                        }
                    }
                    break;
                }
                case "progressbar": {
                    progressAttributes = this.parseProgressBar(node, models[modelName].fields);
                    break;
                }
            }
        }

        return {
            ...cardArchInfo,
            activeActions,
            canOpenRecords: exprToBoolean(xmlDoc.getAttribute("can_open"), true),
            cardArchInfo,
            cardColorField: xmlDoc.getAttribute("highlight_color"),
            className: xmlDoc.getAttribute("class"),
            controls,
            defaultGroupBy,
            handleField,
            headerButtons,
            defaultOrder,
            onCreate: xmlDoc.getAttribute("on_create"),
            openAction,
            quickCreateView: xmlDoc.getAttribute("quick_create_view"),
            recordsDraggable: exprToBoolean(xmlDoc.getAttribute("records_draggable"), true),
            groupsDraggable: exprToBoolean(xmlDoc.getAttribute("groups_draggable"), true),
            limit: limit && parseInt(limit, 10),
            countLimit: countLimit && parseInt(countLimit, 10),
            progressAttributes,
            tooltipInfo,
            examples: xmlDoc.getAttribute("examples"),
        };
    }

    parseProgressBar(progressBar, fields) {
        const attrs = extractAttributes(progressBar, ["field", "colors", "sum_field", "help"]);
        return {
            fieldName: attrs.field,
            colors: JSON.parse(attrs.colors),
            sumField: fields[attrs.sum_field] || false,
            help: attrs.help,
        };
    }

    processButton(node) {
        return processButton(node);
    }
}
