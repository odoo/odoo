// @ts-check
/** @odoo-module native */

import { makeContext } from "@web/core/context";
import { isX2ManyType } from "@web/core/field_types";
import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";
import { _t } from "@web/core/translation";
import { visitXML } from "@web/core/utils/dom/xml";
import { clamp } from "@web/core/utils/format/numbers";
import { faIconClass } from "@web/core/utils/icons";
import { isInvisible } from "@web/search/search_state";
import { DEFAULT_INTERVAL, toGeneratorId } from "@web/search/utils/dates";
import { literalNbsp } from "@web/views/ir/view_ir";
import { irToElement } from "@web/views/ir/view_ir";

const ALL = _t("All");
const DEFAULT_LIMIT = 200;
export const DEFAULT_VIEWS_WITH_SEARCH_PANEL = ["kanban", "list"];

/** @type {Record<string, number>} */
const DEFAULT_PERIOD_WINDOW = {
    start_month: -2,
    end_month: 0,
    start_year: -2,
    end_year: 0,
};

const IMPLAUSIBLE_PERIOD_SPAN = 100;

/**
 * @param {string | null | undefined} iconClass
 * @returns {string | null}
 */
function _normalizeIconClass(iconClass) {
    return iconClass ? faIconClass(iconClass) : null;
}

/**
 * @param {string} context
 * @returns {string[]}
 */
function getContextGroupBy(context) {
    try {
        return makeContext([context]).group_by?.split(":") || [];
    } catch {
        return [];
    }
}

/**
 * @param {string} type
 * @returns {string}
 */
function reduceType(type) {
    if (type === "dateFilter") {
        return "filter";
    }
    if (type === "dateGroupBy") {
        return "groupBy";
    }
    return type;
}

export class SearchArchParser {
    /**
     * @param {{ irFilters?: Record<string, any>[], arch?: string, ir?: import("@web/views/ir/view_ir_schema").ViewIRNode }} searchViewDescription
     * @param {Record<string, Record<string, any>>} fields
     * @param {Record<string, any>} [searchDefaults={}]
     * @param {Record<string, any>} [searchPanelDefaults={}]
     * @param {Record<string, any>} [evalContext={}]
     */
    constructor(
        searchViewDescription,
        fields,
        searchDefaults = {},
        searchPanelDefaults = {},
        evalContext = {},
    ) {
        const { irFilters, arch, ir } = searchViewDescription;

        this.fields = fields || {};
        this.irFilters = irFilters || [];
        /** @type {Element | string} */
        this.arch = ir ? irToElement(ir, { text: literalNbsp }) : arch || "<search/>";
        this.evalContext = evalContext;

        /** @type {((orm: any) => Promise<void>)[]} */
        this.labels = [];
        /** @type {Record<string, any>[][]} */
        this.preSearchItems = [];
        this.searchPanelInfo = {
            className: "",
            viewTypes: [...DEFAULT_VIEWS_WITH_SEARCH_PANEL],
        };
        /** @type {[number, Record<string, any>][]} */
        this.sections = [];

        this.searchDefaults = searchDefaults;
        this.searchPanelDefaults = searchPanelDefaults;

        /** @type {Record<string, any>[]} */
        this.currentGroup = [];
        /** @type {string|null} */
        this.currentTag = null;
        this.groupNumber = 0;
        /** @type {Record<string, any>[]} */
        this.pregroupOfGroupBys = [];

        /** @type {Record<string, any>|null} */
        this.optionsParams = null;
    }

    /** @returns {{ labels: Function[], preSearchItems: Record<string, any>[][], searchPanelInfo: Object, sections: [number, Record<string, any>][] }} */
    parse() {
        visitXML(this.arch, (node, visitChildren) => {
            switch (node.tagName) {
                case "search":
                    this.visitSearch(node, visitChildren);
                    break;
                case "searchpanel":
                    return this.visitSearchPanel(node);
                case "group":
                    this.visitGroup(node, visitChildren);
                    break;
                case "separator":
                    this.visitSeparator();
                    break;
                case "field":
                    this.visitField(node);
                    break;
                case "filter":
                    if (this.optionsParams) {
                        this.visitDateOption(node);
                    } else {
                        this.visitFilter(node, visitChildren);
                    }
                    break;
            }
        });

        return {
            labels: this.labels,
            preSearchItems: this.preSearchItems,
            searchPanelInfo: this.searchPanelInfo,
            sections: this.sections,
        };
    }

    /** @param {string | null} [tag=null] */
    pushGroup(tag = null) {
        if (this.currentGroup.length) {
            if (this.currentTag === "groupBy") {
                this.pregroupOfGroupBys.push(...this.currentGroup);
            } else {
                this.preSearchItems.push(this.currentGroup);
            }
        }
        this.currentTag = tag;
        this.currentGroup = [];
        this.groupNumber++;
    }

    /**
     * @param {Element} node
     * @param {string} fieldType
     * @returns {string}
     */
    defaultOperatorFor(node, fieldType) {
        const type = node.hasAttribute("widget")
            ? /** @type {string} */ (node.getAttribute("widget"))
            : fieldType;
        return ["char", "html", "many2many", "one2many", "text"].includes(type)
            ? "ilike"
            : "=";
    }

    /**
     * @param {Record<string, any>} defaultAutocompleteValue
     * @param {number|number[]} ids
     * @param {Record<string, any>} field
     * @param {(results: Record<string, any>[]) => string} format
     */
    queueDisplayNameLabel(defaultAutocompleteValue, ids, field, format) {
        const { relation, context } = field;
        this.labels.push(async (/** @type {any} */ orm) => {
            let results;
            try {
                results = await orm.silent.call(
                    relation,
                    "read",
                    [ids, ["display_name"]],
                    { context },
                );
            } catch {
                results = [];
            }
            defaultAutocompleteValue.label = format(results);
        });
    }

    /**
     * @param {Record<string, any>} preField
     * @param {Element} node
     * @param {string} name
     */
    applyFieldDefault(preField, node, name) {
        const field = this.fields[name];
        const fieldType = field.type;
        const val = this.searchDefaults[name];
        const value = Array.isArray(val) ? val[0] : val;

        preField.isDefault = true;
        preField.defaultRank = -10;
        preField.defaultAutocompleteValue = {
            label: `${value}`,
            operator: preField.operator || this.defaultOperatorFor(node, fieldType),
            value,
        };

        if (fieldType === "selection") {
            const option = field.selection.find(
                (/** @type {any[]} */ sel) => sel[0] === value,
            );
            if (option) {
                preField.defaultAutocompleteValue.label = option[1];
            }
        } else if (fieldType === "many2one") {
            this.queueDisplayNameLabel(
                preField.defaultAutocompleteValue,
                value,
                field,
                (results) => results[0]?.["display_name"] ?? String(value),
            );
        } else if (
            isX2ManyType(fieldType) &&
            Array.isArray(val) &&
            val.every((v) => Number.isInteger(v) && v > 0)
        ) {
            preField.defaultAutocompleteValue.operator = "in";
            preField.defaultAutocompleteValue.value = val;
            this.queueDisplayNameLabel(
                preField.defaultAutocompleteValue,
                val,
                field,
                (results) =>
                    results.map((r) => r["display_name"]).join(" or ") || String(val),
            );
        }
    }

    /** @param {Element} node */
    visitField(node) {
        this.pushGroup("field");
        /** @type {Record<string, any>} */
        const preField = { type: "field", groupNumber: this.groupNumber };
        if (node.hasAttribute("invisible")) {
            preField.invisible = node.getAttribute("invisible");
        }
        if (node.hasAttribute("domain")) {
            preField.domain = node.getAttribute("domain");
        }
        if (node.hasAttribute("filter_domain")) {
            preField.filterDomain = node.getAttribute("filter_domain");
        } else if (node.hasAttribute("operator")) {
            preField.operator = node.getAttribute("operator");
        }
        if (node.hasAttribute("context")) {
            preField.context = node.getAttribute("context");
        }
        if (node.hasAttribute("name")) {
            const name = node.getAttribute("name");
            if (!this.fields[name]) {
                console.warn(
                    `[search] <field name="${name}">: no such field on the model; ` +
                        `the search field is ignored (check for a typo).`,
                );
                return;
            }
            const fieldType = this.fields[name].type;
            preField.fieldName = name;
            preField.fieldType = fieldType;
            if (fieldType !== "properties" && name in this.searchDefaults) {
                this.applyFieldDefault(preField, node, name);
            }
        } else {
            throw new Error(
                "Invalid search view arch: a <field> node has no 'name' attribute.",
            );
        }
        if (node.hasAttribute("string")) {
            preField.description = node.getAttribute("string");
        } else {
            preField.description = this.fields[preField.fieldName].string;
        }
        this.currentGroup.push(preField);
    }

    /**
     * @param {Element} node
     * @param {Record<string, any>} preSearchItem
     */
    classifyByContext(node, preSearchItem) {
        if (!node.hasAttribute("context")) {
            return;
        }
        const context = node.getAttribute("context");
        const [fieldName, defaultInterval] = getContextGroupBy(context);
        const groupByField = this.fields[fieldName];
        if (!groupByField) {
            preSearchItem.context = context;
            return;
        }
        preSearchItem.type = "groupBy";
        preSearchItem.fieldName = fieldName;
        preSearchItem.fieldType = groupByField.type;
        if (["date", "datetime"].includes(groupByField.type)) {
            preSearchItem.type = "dateGroupBy";
            preSearchItem.defaultIntervalId = defaultInterval || DEFAULT_INTERVAL;
        }
    }

    /**
     * @param {Element} node
     * @param {string} fieldName
     * @param {"month"|"year"} unit
     * @returns {[number, number]}
     */
    readPeriodWindow(node, fieldName, unit) {
        const read = (/** @type {string} */ attribute) => {
            const raw = node.getAttribute(attribute);
            if (!raw) {
                return DEFAULT_PERIOD_WINDOW[attribute];
            }
            const value = Number(raw);
            if (!Number.isInteger(value)) {
                console.warn(
                    `[search] <filter date="${fieldName}">: ${attribute}="${raw}" is not ` +
                        `a whole number; using the default ` +
                        `(${DEFAULT_PERIOD_WINDOW[attribute]}).`,
                );
                return DEFAULT_PERIOD_WINDOW[attribute];
            }
            return value;
        };
        let start = read(`start_${unit}`);
        let end = read(`end_${unit}`);
        if (end < start) {
            console.warn(
                `[search] <filter date="${fieldName}">: end_${unit} (${end}) is lower ` +
                    `than start_${unit} (${start}); swapping them.`,
            );
            [start, end] = [end, start];
        }
        if (end - start + 1 > IMPLAUSIBLE_PERIOD_SPAN) {
            console.warn(
                `[search] <filter date="${fieldName}">: start_${unit}/end_${unit} span ` +
                    `${end - start + 1} ${unit}s, which renders that many menu rows. ` +
                    `Kept as declared -- check the arch.`,
            );
        }
        return [start, end];
    }

    /**
     * @param {Element} node
     * @param {Record<string, any>} preSearchItem
     * @param {() => void} visitChildren
     */
    applyDateFilter(node, preSearchItem, visitChildren) {
        const fieldName = node.getAttribute("date");
        const dateField = this.fields[fieldName];
        preSearchItem.type = "dateFilter";
        preSearchItem.fieldName = fieldName;
        preSearchItem.fieldType = dateField.type;

        const [startMonth, endMonth] = this.readPeriodWindow(node, fieldName, "month");
        const [startYear, endYear] = this.readPeriodWindow(node, fieldName, "year");
        /** @type {Record<string, any>} */
        const optionsParams = {
            startYear,
            endYear,
            startMonth,
            endMonth,
            customOptions: [],
        };

        const defaultOffset = clamp(
            0,
            optionsParams.startMonth,
            optionsParams.endMonth,
        );
        preSearchItem.defaultGeneratorIds = [toGeneratorId("month", defaultOffset)];
        if (node.hasAttribute("default_period")) {
            preSearchItem.defaultGeneratorIds = node
                .getAttribute("default_period")
                .split(",");
        }

        this.optionsParams = optionsParams;
        try {
            visitChildren();
        } finally {
            this.optionsParams = null;
        }
        preSearchItem.optionsParams = optionsParams;
    }

    /**
     * @param {Element} node
     * @param {Record<string, any>} preSearchItem
     */
    describeFilter(node, preSearchItem) {
        if (node.hasAttribute("string")) {
            preSearchItem.description = node.getAttribute("string");
        } else if (preSearchItem.fieldName && this.fields[preSearchItem.fieldName]) {
            preSearchItem.description = this.fields[preSearchItem.fieldName].string;
        } else if (node.hasAttribute("help")) {
            preSearchItem.description = node.getAttribute("help");
        } else if (node.hasAttribute("name")) {
            preSearchItem.description = node.getAttribute("name");
        } else {
            preSearchItem.description = "Ω";
        }
    }

    /**
     * @param {Record<string, any>} preSearchItem
     * @param {string} name
     */
    applyFilterDefault(preSearchItem, name) {
        preSearchItem.isDefault = true;
        const value = this.searchDefaults[name];
        if (["groupBy", "dateGroupBy"].includes(preSearchItem.type)) {
            preSearchItem.defaultRank = typeof value === "number" ? value : 100;
        } else {
            preSearchItem.defaultRank = -5;
        }
        if (
            preSearchItem.type === "dateFilter" &&
            typeof value === "string" &&
            !/^(true|1)$/i.test(value)
        ) {
            preSearchItem.defaultGeneratorIds = value.split(",");
        }
    }

    /**
     * @param {Element} node
     * @param {() => void} visitChildren
     */
    visitFilter(node, visitChildren) {
        /** @type {Record<string, any>} */
        const preSearchItem = { type: "filter" };
        this.classifyByContext(node, preSearchItem);

        const dateFieldName = node.getAttribute("date");
        if (dateFieldName && !this.fields[dateFieldName]) {
            console.warn(
                `[search] <filter date="${dateFieldName}">: no such field on the ` +
                    `model; the date filter is ignored (check for a typo).`,
            );
            return;
        }

        if (reduceType(preSearchItem.type) !== this.currentTag) {
            this.pushGroup(reduceType(preSearchItem.type));
        }

        if (preSearchItem.type === "filter") {
            if (dateFieldName) {
                this.applyDateFilter(node, preSearchItem, visitChildren);
            }
            preSearchItem.domain = node.getAttribute("domain") || "[]";
        }
        if (node.hasAttribute("invisible")) {
            preSearchItem.invisible = node.getAttribute("invisible");
        }
        preSearchItem.groupNumber = this.groupNumber;
        if (node.hasAttribute("name")) {
            const name = node.getAttribute("name");
            preSearchItem.name = name;
            if (name in this.searchDefaults) {
                this.applyFilterDefault(preSearchItem, name);
            }
        }
        this.describeFilter(node, preSearchItem);
        this.currentGroup.push(preSearchItem);
    }

    /** @param {Element} node */
    visitDateOption(node) {
        /** @type {Record<string, any>} */
        const preDateOption = { type: "dateOption" };
        for (const attribute of ["name", "string", "domain"]) {
            if (!node.getAttribute(attribute)) {
                throw new Error(`Attribute "${attribute}" is missing.`);
            }
        }
        preDateOption.id = `custom_${node.getAttribute("name")}`;
        preDateOption.description = node.getAttribute("string");
        preDateOption.domain = node.getAttribute("domain");
        this.optionsParams.customOptions.push(preDateOption);
    }

    /**
     * @param {Element} node
     * @param {() => void} visitChildren
     */
    visitGroup(node, visitChildren) {
        this.pushGroup();
        visitChildren();
        this.pushGroup();
    }

    /**
     * @param {Element} node
     * @param {() => void} visitChildren
     */
    visitSearch(node, visitChildren) {
        visitChildren();
        this.pushGroup();
        if (this.pregroupOfGroupBys.length) {
            this.preSearchItems.push(this.pregroupOfGroupBys);
        }
    }

    /**
     * @param {Element} node
     * @param {number} sectionId
     * @returns {Record<string, any>}
     */
    getPanelSection(node, sectionId) {
        /** @type {Record<string, any>} */
        const attrs = {};
        for (const attrName of node.getAttributeNames()) {
            attrs[attrName] = node.getAttribute(attrName);
        }

        const type = attrs.select === "multi" ? "filter" : "category";
        /** @type {Record<string, any>} */
        const section = {
            color: attrs.color || null,
            description: attrs.string || this.fields[attrs.name]?.string || attrs.name,
            enableCounters: evaluateBooleanExpr(attrs.enable_counters),
            expand: evaluateBooleanExpr(attrs.expand),
            fieldName: attrs.name,
            icon: _normalizeIconClass(attrs.icon),
            id: sectionId,
            limit: evaluateExpr(attrs.limit || String(DEFAULT_LIMIT)),
            type,
            values: new Map(),
        };
        if (type === "category") {
            const categoryDefault = this.searchPanelDefaults[attrs.name];
            section.activeValueId = Array.isArray(categoryDefault)
                ? categoryDefault[0]
                : categoryDefault;
            section.icon = section.icon || "fa-solid fa-folder";
            section.hierarchize = evaluateBooleanExpr(attrs.hierarchize || "1");
            section.depth = attrs.depth ? Number.parseInt(attrs.depth, 10) : 0;
            section.values.set(false, {
                childrenIds: [],
                display_name: ALL.toString(),
                id: false,
                bold: true,
                parentId: false,
            });
        } else {
            section.domain = attrs.domain || "[]";
            section.groupBy = attrs.groupby || null;
            section.icon = section.icon || "fa-solid fa-filter";
        }
        return section;
    }

    /**
     * @param {Element} searchPanelNode
     * @returns {false}
     */
    visitSearchPanel(searchPanelNode) {
        let hasCategoryWithCounters = false;
        let hasFilterWithDomain = false;
        let nextSectionId = 1;

        if (searchPanelNode.hasAttribute("class")) {
            this.searchPanelInfo.className = searchPanelNode.getAttribute("class");
        }
        if (searchPanelNode.hasAttribute("view_types")) {
            this.searchPanelInfo.viewTypes = searchPanelNode
                .getAttribute("view_types")
                .split(",");
        }

        for (const node of searchPanelNode.children) {
            if (node.tagName !== "field") {
                continue;
            }
            const sectionId = nextSectionId++;
            if (this.isHidden(node)) {
                continue;
            }
            const section = this.getPanelSection(node, sectionId);
            if (section.type === "category") {
                hasCategoryWithCounters =
                    hasCategoryWithCounters || section.enableCounters;
            } else {
                hasFilterWithDomain = hasFilterWithDomain || section.domain !== "[]";
            }
            this.sections.push([section.id, section]);
        }

        if (hasCategoryWithCounters && hasFilterWithDomain) {
            for (const section of this.sections) {
                if (section[1].type === "category") {
                    section[1].enableCounters = false;
                }
            }
            console.warn(
                "Warning: categories with counters are incompatible with filters having a domain attribute.",
                "All category counters have been disabled to avoid inconsistencies.",
            );
        }

        return false;
    }

    /**
     * @param {Element} node
     * @returns {boolean}
     */
    isHidden(node) {
        return isInvisible(node.getAttribute("invisible"), this.evalContext);
    }

    visitSeparator() {
        this.pushGroup();
    }
}
