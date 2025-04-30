import { evaluateExpr } from "@web/core/py_js/py";
import { exprToBoolean } from "@web/core/utils/strings";
import { visitXML } from "@web/core/utils/xml";
import { Field } from "@web/views/fields/field";

const FIELD_ATTRIBUTE_NAMES = [
    "date_start",
    "date_delay",
    "date_stop",
    "all_day",
    "create_name_field",
    "color",
];
const SCALES = ["day", "week", "month", "year"];

export class CalendarParseArchError extends Error {}

export class CalendarArchParser {
    parse(xmlDoc, models, modelName) {
        const fields = models[modelName].fields;
        const fieldNames = new Set(fields.display_name ? ["display_name"] : []);
        const fieldMapping = {};
        for (const fieldAttrName of FIELD_ATTRIBUTE_NAMES) {
            if (xmlDoc.hasAttribute(fieldAttrName)) {
                const fieldName = xmlDoc.getAttribute(fieldAttrName);
                fieldNames.add(fieldName);
                fieldMapping[fieldAttrName] = fieldName;
            }
        }
        const aggregate = xmlDoc.getAttribute("aggregate") || null;
        if (aggregate) {
            fieldNames.add(aggregate.split(":")[0]);
        }

        let scales = [...SCALES];
        const scalesAttr = xmlDoc.getAttribute("scales");
        if (scalesAttr) {
            scales = scalesAttr.split(",").filter((scale) => SCALES.includes(scale));
        }
        let scale = scales.includes("week") ? "week" : scales[0];
        if (xmlDoc.hasAttribute("mode")) {
            scale = xmlDoc.getAttribute("mode");
        }

        const canCreate = exprToBoolean(xmlDoc.getAttribute("create"), true);
        const canDelete = exprToBoolean(xmlDoc.getAttribute("delete"), true);
        const canEdit = exprToBoolean(xmlDoc.getAttribute("edit"), true);

        const eventLimit = xmlDoc.hasAttribute("event_limit")
            ? evaluateExpr(xmlDoc.getAttribute("event_limit"))
            : 5;
        const formViewId = parseInt(xmlDoc.getAttribute("form_view_id"), 10) || false;
        const hasEditDialog = exprToBoolean(xmlDoc.getAttribute("event_open_popup"));
        const isDateHidden = exprToBoolean(xmlDoc.getAttribute("hide_date"));
        const isTimeHidden = exprToBoolean(xmlDoc.getAttribute("hide_time"));
        const jsClass = xmlDoc.getAttribute("js_class") || null;
        const monthOverflow = exprToBoolean(xmlDoc.getAttribute("month_overflow"), true);
        const multiCreateView = xmlDoc.getAttribute("multi_create_view");
        const quickCreate = exprToBoolean(xmlDoc.getAttribute("quick_create"), true);
        const quickCreateViewId =
            (quickCreate && parseInt(xmlDoc.getAttribute("quick_create_view_id"), 10)) || null;
        const showDatePicker = exprToBoolean(xmlDoc.getAttribute("show_date_picker"), true);
        const showUnusualDays = exprToBoolean(xmlDoc.getAttribute("show_unusual_days"));

        const popoverFieldNodes = {};
        const filtersInfo = {};
        visitXML(xmlDoc, (node) => {
            switch (node.tagName) {
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
                    popoverFieldNodes[fieldName] = fieldInfo;

                    if (!node.hasAttribute("invisible") || node.hasAttribute("filters")) {
                        if (
                            node.hasAttribute("avatar_field") ||
                            node.hasAttribute("write_model") ||
                            node.hasAttribute("write_field") ||
                            node.hasAttribute("color") ||
                            node.hasAttribute("filters")
                        ) {
                            const field = fields[fieldName];
                            filtersInfo[fieldName] = filtersInfo[fieldName] || {
                                avatarFieldName: null,
                                colorFieldName: null,
                                context: fieldInfo.context || "{}",
                                fieldName,
                                filterFieldName: null,
                                label: field.string,
                                resModel: field.relation,
                                writeFieldName: null,
                                writeResModel: null,
                            };
                            const filterInfo = filtersInfo[fieldName];
                            filterInfo.avatarFieldName = node.getAttribute("avatar_field") || null;
                            filterInfo.colorFieldName =
                                (node.hasAttribute("filters") && node.getAttribute("color")) ||
                                null;
                            filterInfo.filterFieldName = node.getAttribute("filter_field") || null;
                            filterInfo.writeFieldName = node.getAttribute("write_field") || null;
                            filterInfo.writeResModel = node.getAttribute("write_model") || null;
                        }
                    }
                    break;
                }
            }
        });

        if (!fieldMapping.date_start) {
            throw new CalendarParseArchError(`Calendar view must define "date_start" attribute.`);
        }
        if (!scales.includes(scale)) {
            throw new CalendarParseArchError(`Calendar view cannot display mode: ${scale}`);
        }
        if (!Number.isInteger(eventLimit)) {
            throw new CalendarParseArchError(`Calendar view's event limit should be a number`);
        }

        return {
            aggregate,
            canCreate,
            canDelete,
            canEdit,
            eventLimit,
            fieldMapping,
            fieldNames: [...fieldNames],
            filtersInfo,
            formViewId,
            hasEditDialog,
            multiCreateView,
            quickCreate,
            quickCreateViewId,
            isDateHidden,
            isTimeHidden,
            monthOverflow,
            popoverFieldNodes,
            scale,
            scales,
            showUnusualDays,
            showDatePicker,
        };
    }
}
