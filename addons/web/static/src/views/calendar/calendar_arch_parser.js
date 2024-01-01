/** @odoo-module **/

import { evaluateExpr } from "@web/core/py_js/py";
import { XMLParser } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";
import { archParseBoolean } from "@web/views/utils";

const FIELD_ATTRIBUTE_NAMES = [
    "date_start",
    "date_delay",
    "date_stop",
    "all_day",
    "recurrence_update",
    "create_name_field",
    "color",
];
const SCALES = ["day", "week", "month", "year"];

export class CalendarParseArchError extends Error {}

export class CalendarArchParser extends XMLParser {
    parse(arch, models, modelName) {
        const fields = models[modelName];
        const fieldNames = new Set(fields.display_name ? ["display_name"] : []);
        const fieldMapping = { date_start: "date_start" };
        let jsClass = null;
        let eventLimit = 5;
        let scales = [...SCALES];
        let scale = "week";
        let canCreate = true;
        let canDelete = true;
        let hasQuickCreate = true;
        let hasEditDialog = false;
        let showUnusualDays = false;
        let isDateHidden = false;
        let isTimeHidden = false;
        let formViewId = false;
        const popoverFields = {};
        const filtersInfo = {};

        this.visitXML(arch, (node) => {
            switch (node.tagName) {
                case "calendar": {
                    if (!node.hasAttribute("date_start")) {
                        throw new CalendarParseArchError(
                            `Calendar view has not defined "date_start" attribute.`
                        );
                    }

                    jsClass = node.getAttribute("js_class");

                    for (const fieldAttrName of FIELD_ATTRIBUTE_NAMES) {
                        if (node.hasAttribute(fieldAttrName)) {
                            const fieldName = node.getAttribute(fieldAttrName);
                            fieldNames.add(fieldName);
                            fieldMapping[fieldAttrName] = fieldName;
                        }
                    }

                    if (node.hasAttribute("event_limit")) {
                        eventLimit = evaluateExpr(node.getAttribute("event_limit"));
                        if (!Number.isInteger(eventLimit)) {
                            throw new CalendarParseArchError(
                                `Calendar view's event limit should be a number`
                            );
                        }
                    }
                    if (node.hasAttribute("scales")) {
                        const scalesAttr = node.getAttribute("scales");
                        scales = scalesAttr.split(",").filter((scale) => SCALES.includes(scale));
                    }
                    if (node.hasAttribute("mode")) {
                        scale = node.getAttribute("mode");
                        if (!scales.includes(scale)) {
                            throw new CalendarParseArchError(
                                `Calendar view cannot display mode: ${scale}`
                            );
                        }
                    }
                    if (node.hasAttribute("create")) {
                        canCreate = archParseBoolean(node.getAttribute("create"), true);
                    }
                    if (node.hasAttribute("delete")) {
                        canDelete = archParseBoolean(node.getAttribute("delete"), true);
                    }
                    if (node.hasAttribute("quick_add")) {
                        // Don't use archParseBoolean from `utils.js` because it does not interpret integers
                        hasQuickCreate =  !/^(false|0)$/i.test(node.getAttribute("quick_add"));
                    }
                    if (node.hasAttribute("event_open_popup")) {
                        hasEditDialog = archParseBoolean(node.getAttribute("event_open_popup"));
                    }
                    if (node.hasAttribute("show_unusual_days")) {
                        showUnusualDays = archParseBoolean(node.getAttribute("show_unusual_days"));
                    }
                    if (node.hasAttribute("hide_date")) {
                        isDateHidden = archParseBoolean(node.getAttribute("hide_date"));
                    }
                    if (node.hasAttribute("hide_time")) {
                        isTimeHidden = archParseBoolean(node.getAttribute("hide_time"));
                    }
                    if (node.hasAttribute("form_view_id")) {
                        formViewId = parseInt(node.getAttribute("form_view_id"), 10);
                    }

                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name");
                    fieldNames.add(fieldName);

                    const fieldInfo = Field.parseFieldNode(
                        node,
                        models,
                        modelName,
                        "calendar",
                        jsClass
                    );
                    popoverFields[fieldName] = fieldInfo;

                    const field = fields[fieldName];
                    if (!node.hasAttribute("invisible") || node.hasAttribute("filters")) {
                        let filterInfo = null;
                        if (
                            node.hasAttribute("avatar_field") ||
                            node.hasAttribute("write_model") ||
                            node.hasAttribute("write_field") ||
                            node.hasAttribute("color") ||
                            node.hasAttribute("filters")
                        ) {
                            filtersInfo[fieldName] = filtersInfo[fieldName] || {
                                avatarFieldName: null,
                                colorFieldName: null,
                                fieldName,
                                filterFieldName: null,
                                label: field.string,
                                resModel: field.relation,
                                writeFieldName: null,
                                writeResModel: null,
                            };
                            filterInfo = filtersInfo[fieldName];
                        }
                        if (node.hasAttribute("filter_field")) {
                            filterInfo.filterFieldName = node.getAttribute("filter_field");
                        }
                        if (node.hasAttribute("avatar_field")) {
                            filterInfo.avatarFieldName = node.getAttribute("avatar_field");
                        }
                        if (node.hasAttribute("write_model")) {
                            filterInfo.writeResModel = node.getAttribute("write_model");
                        }
                        if (node.hasAttribute("write_field")) {
                            filterInfo.writeFieldName = node.getAttribute("write_field");
                        }
                        if (node.hasAttribute("filters")) {
                            if (node.hasAttribute("color")) {
                                filterInfo.colorFieldName = node.getAttribute("color");
                            }
                            if (node.hasAttribute("avatar_field") && field.relation) {
                                if (
                                    field.relation.includes([
                                        "res.users",
                                        "res.partners",
                                        "hr.employee",
                                    ])
                                ) {
                                    filterInfo.avatarFieldName = "image_128";
                                }
                            }
                        }
                    }

                    break;
                }
            }
        });

        return {
            canCreate,
            canDelete,
            eventLimit,
            fieldMapping,
            fieldNames: [...fieldNames],
            filtersInfo,
            formViewId,
            hasEditDialog,
            hasQuickCreate,
            isDateHidden,
            isTimeHidden,
            popoverFields,
            scale,
            scales,
            showUnusualDays,
        };
    }
}
