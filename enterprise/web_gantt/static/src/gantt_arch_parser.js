import { getLocalYearAndWeek } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { exprToBoolean } from "@web/core/utils/strings";
import { visitXML } from "@web/core/utils/xml";
import { getActiveActions } from "@web/views/utils";

const DECORATIONS = [
    "decoration-danger",
    "decoration-info",
    "decoration-secondary",
    "decoration-success",
    "decoration-warning",
];
const PARTS = { full: 1, half: 2, quarter: 4 };
const SCALES = {
    day: {
        // determines subcolumns
        cellPrecisions: { full: 60, half: 30, quarter: 15 },
        defaultPrecision: "full",
        time: "minute",
        unitDescription: _t("minutes"),

        // determines columns
        interval: "hour",
        minimalColumnWidth: 40,

        // determines column groups
        unit: "day",
        groupHeaderFormatter: (date) => date.toFormat("dd MMMM yyyy"),

        defaultRange: { unit: "day", count: 3 },
    },
    week: {
        cellPrecisions: { full: 24, half: 12 },
        defaultPrecision: "half",
        time: "hour",
        unitDescription: _t("hours"),

        interval: "day",
        minimalColumnWidth: 192,
        colHeaderFormatter: (date) => date.toFormat("dd"),

        unit: "week",
        groupHeaderFormatter: formatLocalWeekYear,

        defaultRange: { unit: "week", count: 3 },
    },
    week_2: {
        cellPrecisions: { full: 24, half: 12 },
        defaultPrecision: "half",
        time: "hour",
        unitDescription: _t("hours"),

        interval: "day",
        minimalColumnWidth: 96,
        colHeaderFormatter: (date) => date.toFormat("dd"),

        unit: "week",
        groupHeaderFormatter: formatLocalWeekYear,

        defaultRange: { unit: "week", count: 6 },
    },
    month: {
        cellPrecisions: { full: 24, half: 12 },
        defaultPrecision: "half",
        time: "hour",
        unitDescription: _t("hours"),

        interval: "day",
        minimalColumnWidth: 50,
        colHeaderFormatter: (date) => date.toFormat("dd"),

        unit: "month",
        groupHeaderFormatter: (date, env) => date.toFormat(env.isSmall ? "MMM yyyy" : "MMMM yyyy"),

        defaultRange: { unit: "month", count: 3 },
    },
    month_3: {
        cellPrecisions: { full: 24, half: 12 },
        defaultPrecision: "half",
        time: "hour",
        unitDescription: _t("hours"),

        interval: "day",
        minimalColumnWidth: 18,
        colHeaderFormatter: (date) => date.toFormat("dd"),

        unit: "month",
        groupHeaderFormatter: (date, env) => date.toFormat(env.isSmall ? "MMM yyyy" : "MMMM yyyy"),

        defaultRange: { unit: "month", count: 6 },
    },
    year: {
        cellPrecisions: { full: 1 },
        defaultPrecision: "full",
        time: "month",
        unitDescription: _t("months"),

        interval: "month",
        minimalColumnWidth: 60,
        colHeaderFormatter: (date, env) => date.toFormat(env.isSmall ? "MMM" : "MMMM"),

        unit: "year",
        groupHeaderFormatter: (date) => date.toFormat("yyyy"),

        defaultRange: { unit: "year", count: 1 },
    },
};

/**
 * Formats a date to a `'W'W kkkk` datetime string, in the user's locale settings.
 *
 * @param {Date|luxon.DateTime} date
 * @returns {string}
 */
function formatLocalWeekYear(date) {
    const { year, week } = getLocalYearAndWeek(date);
    return `W${week} ${year}`;
}

function getPreferedScaleId(scaleId, scales) {
    // we assume that scales is not empty
    if (scaleId in scales) {
        return scaleId;
    }
    const scaleIds = Object.keys(SCALES);
    const index = scaleIds.findIndex((id) => id === scaleId);
    for (let j = index - 1; j >= 0; j--) {
        const id = scaleIds[j];
        if (id in scales) {
            return id;
        }
    }
    for (let j = index + 1; j < scaleIds.length; j++) {
        const id = scaleIds[j];
        if (id in scales) {
            return id;
        }
    }
}

const RANGES = {
    day: { scaleId: "day", description: _t("Today") },
    week: { scaleId: "week", description: _t("This week") },
    month: { scaleId: "month", description: _t("This month") },
    quarter: { scaleId: "month_3", description: _t("This quarter") },
    year: { scaleId: "year", description: _t("This year") },
};

export class GanttArchParser {
    parse(arch) {
        let infoFromRootNode;
        const decorationFields = [];
        const popoverArchParams = {
            displayGenericButtons: true,
            bodyTemplate: null,
            footerTemplate: null,
        };

        visitXML(arch, (node) => {
            switch (node.tagName) {
                case "gantt": {
                    infoFromRootNode = getInfoFromRootNode(node);
                    break;
                }
                case "field": {
                    const fieldName = node.getAttribute("name");
                    decorationFields.push(fieldName);
                    break;
                }
                case "templates": {
                    const body = node.querySelector("[t-name=gantt-popover]") || null;
                    if (body) {
                        popoverArchParams.bodyTemplate = body.cloneNode(true);
                        popoverArchParams.bodyTemplate.removeAttribute("t-name");
                        const footer = popoverArchParams.bodyTemplate.querySelector("footer");
                        if (footer) {
                            popoverArchParams.displayGenericButtons = false;
                            footer.remove();
                            const footerTemplate = new Document().createElement("t");
                            footerTemplate.append(...footer.children);
                            popoverArchParams.footerTemplate = footerTemplate;
                            const replace = footer.getAttribute("replace");
                            if (replace && !exprToBoolean(replace)) {
                                popoverArchParams.displayGenericButtons = true;
                            }
                        }
                    }
                }
            }
        });

        return {
            ...infoFromRootNode,
            decorationFields,
            popoverArchParams,
        };
    }
}

function getInfoFromRootNode(rootNode) {
    const attrs = {};
    for (const { name, value } of rootNode.attributes) {
        attrs[name] = value;
    }

    const { create: canCreate, delete: canDelete, edit: canEdit } = getActiveActions(rootNode);
    const canCellCreate = exprToBoolean(attrs.cell_create, true) && canCreate;
    const canPlan = exprToBoolean(attrs.plan, true) && canEdit;

    let consolidationMaxField;
    let consolidationMaxValue;
    const consolidationMax = attrs.consolidation_max ? evaluateExpr(attrs.consolidation_max) : {};
    if (Object.keys(consolidationMax).length > 0) {
        consolidationMaxField = Object.keys(consolidationMax)[0];
        consolidationMaxValue = consolidationMax[consolidationMaxField];
    }

    const consolidationParams = {
        excludeField: attrs.consolidation_exclude,
        field: attrs.consolidation,
        maxField: consolidationMaxField,
        maxValue: consolidationMaxValue,
    };

    const dependencyField = attrs.dependency_field || null;
    const dependencyEnabled = !!dependencyField;
    const dependencyInvertedField = attrs.dependency_inverted_field || null;

    const allowedScales = [];
    if (attrs.scales) {
        for (const key of attrs.scales.split(",")) {
            if (SCALES[key]) {
                allowedScales.push(key);
            }
        }
    }
    if (allowedScales.length === 0) {
        allowedScales.push(...Object.keys(SCALES));
    }

    let defaultScale = attrs.default_scale;
    if (defaultScale) {
        if (!allowedScales.includes(defaultScale) && SCALES[defaultScale]) {
            allowedScales.push(defaultScale);
        }
    } else if (allowedScales.includes("month")) {
        defaultScale = "month";
    } else {
        defaultScale = allowedScales[0];
    }

    // Cell precision
    const cellPrecisions = {};

    // precision = {'day': 'hour:half', 'week': 'day:half', 'month': 'day', 'year': 'month:quarter'}
    const precisionAttrs = attrs.precision ? evaluateExpr(attrs.precision) : {};
    for (const scaleId in SCALES) {
        if (precisionAttrs[scaleId]) {
            const precision = precisionAttrs[scaleId].split(":"); // hour:half
            // Note that precision[0] (which is the cell interval) is not
            // taken into account right now because it is no customizable.
            if (
                precision[1] &&
                Object.keys(SCALES[scaleId].cellPrecisions).includes(precision[1])
            ) {
                cellPrecisions[scaleId] = precision[1];
            }
        }
        cellPrecisions[scaleId] ||= SCALES[scaleId].defaultPrecision;
    }

    const scales = {};
    for (const scaleId of allowedScales) {
        const precision = cellPrecisions[scaleId];
        const referenceScale = SCALES[scaleId];
        scales[scaleId] = {
            ...referenceScale,
            cellPart: PARTS[precision],
            cellTime: referenceScale.cellPrecisions[precision],
            id: scaleId,
            unitDescription: referenceScale.unitDescription.toString(),
        };
        // protect SCALES content
        delete scales[scaleId].cellPrecisions;
    }

    const ranges = {};
    for (const rangeId in RANGES) {
        const referenceRange = RANGES[rangeId];
        const { groupHeaderFormatter } = SCALES[referenceRange.scaleId];
        ranges[rangeId] = {
            ...referenceRange,
            groupHeaderFormatter,
            id: rangeId,
            scaleId: getPreferedScaleId(referenceRange.scaleId, scales),
            description: referenceRange.description.toString(),
        };
    }

    let pillDecorations = null;
    for (const decoration of DECORATIONS) {
        if (decoration in attrs) {
            if (!pillDecorations) {
                pillDecorations = {};
            }
            pillDecorations[decoration] = attrs[decoration];
        }
    }

    return {
        canCellCreate,
        canCreate,
        canDelete,
        canEdit,
        canPlan,
        colorField: attrs.color,
        computePillDisplayName: !!attrs.pill_label,
        consolidationParams,
        createAction: attrs.on_create || null,
        dateStartField: attrs.date_start,
        dateStopField: attrs.date_stop,
        defaultGroupBy: attrs.default_group_by ? attrs.default_group_by.split(",") : [],
        defaultRange: attrs.default_range,
        defaultScale,
        dependencyEnabled,
        dependencyField,
        dependencyInvertedField,
        disableDrag: exprToBoolean(attrs.disable_drag_drop),
        displayMode: attrs.display_mode || "dense",
        displayTotalRow: exprToBoolean(attrs.total_row),
        displayUnavailability: exprToBoolean(attrs.display_unavailability),
        formViewId: attrs.form_view_id ? parseInt(attrs.form_view_id, 10) : false,
        offset: attrs.offset,
        pagerLimit: attrs.groups_limit ? parseInt(attrs.groups_limit, 10) : null,
        pillDecorations,
        progressBarFields: attrs.progress_bar ? attrs.progress_bar.split(",") : null,
        progressField: attrs.progress || null,
        ranges,
        scales,
        string: attrs.string || _t("Gantt View").toString(),
        thumbnails: attrs.thumbnails ? evaluateExpr(attrs.thumbnails) : {},
    };
}
