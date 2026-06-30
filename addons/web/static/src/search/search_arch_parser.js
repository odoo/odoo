import { makeContext } from "@web/core/context";
import { _t } from "@web/core/l10n/translation";
import { evaluateBooleanExpr, evaluateExpr } from "@web/core/py_js/py";
import { clamp } from "@web/core/utils/numbers";
import { visitXML } from "@web/core/utils/xml";
import { DEFAULT_INTERVAL, toGeneratorId } from "@web/search/utils/dates";

const ALL = _t("All");
const DEFAULT_LIMIT = 200;
const DEFAULT_VIEWS_WITH_SEARCH_PANEL = ["kanban", "list"];

/**
 * Returns the split 'group_by' key from the given context attribute.
 * This helper accepts any invalid context or one that does not have
 * a valid 'group_by' key, and falls back to an empty list.
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
    constructor(searchViewDescription, fields, searchDefaults = {}, searchPanelDefaults = {}) {
        const { irFilters, arch } = searchViewDescription;

        this.fields = fields || {};
        this.irFilters = irFilters || [];
        this.arch = arch || "<search/>";

        this.labels = [];
        this.preSearchItems = [];
        this.searchPanelInfo = {
            className: "",
            viewTypes: DEFAULT_VIEWS_WITH_SEARCH_PANEL,
        };
        this.sections = [];

        this.searchDefaults = searchDefaults;
        this.searchPanelDefaults = searchPanelDefaults;

        this.currentGroup = [];
        this.currentTag = null;
        this.groupNumber = 0;
        this.pregroupOfGroupBys = [];

        this.optionsParams = null;
    }

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

    visitField(node) {
        this.pushGroup("field");
        const preField = { type: "field" };
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
                throw Error(`Unknown field ${name}`);
            }
            const fieldType = this.fields[name].type;
            preField.fieldName = name;
            preField.fieldType = fieldType;
            if (fieldType !== "properties" && name in this.searchDefaults) {
                preField.isDefault = true;
                const val = this.searchDefaults[name];
                const value = Array.isArray(val) ? val[0] : val;
                let operator = preField.operator;
                if (!operator) {
                    let type = fieldType;
                    if (node.hasAttribute("widget")) {
                        type = node.getAttribute("widget");
                    }
                    // Note: many2one as a default filter will have a
                    // numeric value instead of a string => we want "="
                    // instead of "ilike".
                    if (["char", "html", "many2many", "one2many", "text"].includes(type)) {
                        operator = "ilike";
                    } else {
                        operator = "=";
                    }
                }
                preField.defaultRank = -10;
                const { selection, context, relation } = this.fields[name];
                preField.defaultAutocompleteValue = { label: `${value}`, operator, value };
                if (fieldType === "selection") {
                    const option = selection.find((sel) => sel[0] === value);
                    if (!option) {
                        throw Error();
                    }
                    preField.defaultAutocompleteValue.label = option[1];
                } else if (fieldType === "many2one") {
                    this.labels.push((orm) =>
                        orm
                            .call(relation, "read", [value, ["display_name"]], { context })
                            .then((results) => {
                                preField.defaultAutocompleteValue.label =
                                    results[0]["display_name"];
                            })
                    );
                } else if (
                    ["many2many", "one2many"].includes(fieldType) &&
                    Array.isArray(val) &&
                    val.every((v) => Number.isInteger(v) && v > 0)
                ) {
                    preField.defaultAutocompleteValue.operator = "in";
                    preField.defaultAutocompleteValue.value = val;
                    this.labels.push((orm) =>
                        orm
                            .call(relation, "read", [val, ["display_name"]], { context })
                            .then((results) => {
                                preField.defaultAutocompleteValue.label = `${results
                                    .map((r) => r["display_name"])
                                    .join(" or ")}`;
                            })
                    );
                }
            }
        } else {
            throw Error(); //but normally this should have caught earlier with view arch validation server side
        }
        if (node.hasAttribute("string")) {
            preField.description = node.getAttribute("string");
        } else if (preField.fieldName) {
            preField.description = this.fields[preField.fieldName].string;
        } else {
            preField.description = "Ω";
        }
        this.currentGroup.push(preField);
    }

    visitFilter(node, visitChildren) {
        const preSearchItem = { type: "filter" };
        if (node.hasAttribute("context")) {
            const context = node.getAttribute("context");
            const [fieldName, defaultInterval] = getContextGroupBy(context);
            const groupByField = this.fields[fieldName];
            if (groupByField) {
                preSearchItem.type = "groupBy";
                preSearchItem.fieldName = fieldName;
                preSearchItem.fieldType = groupByField.type;
                if (["date", "datetime"].includes(groupByField.type)) {
                    preSearchItem.type = "dateGroupBy";
                    preSearchItem.defaultIntervalId = defaultInterval || DEFAULT_INTERVAL;
                }
            } else {
                preSearchItem.context = context;
            }
        }
        if (reduceType(preSearchItem.type) !== this.currentTag) {
            this.pushGroup(reduceType(preSearchItem.type));
        }
        if (preSearchItem.type === "filter") {
            if (node.hasAttribute("date")) {
                const fieldName = node.getAttribute("date");
                preSearchItem.type = "dateFilter";
                preSearchItem.fieldName = fieldName;
                preSearchItem.fieldType = this.fields[fieldName].type;
                const optionsParams = {
                    startYear: Number(node.getAttribute("start_year") || -2),
                    endYear: Number(node.getAttribute("end_year") || 0),
                    startMonth: Number(node.getAttribute("start_month") || -2),
                    endMonth: Number(node.getAttribute("end_month") || 0),
                    customOptions: [],
                };
                const defaultOffset = clamp(optionsParams.startMonth, optionsParams.endMonth, 0);
                preSearchItem.defaultGeneratorIds = [toGeneratorId("month", defaultOffset)];
                if (node.hasAttribute("default_period")) {
                    preSearchItem.defaultGeneratorIds = node
                        .getAttribute("default_period")
                        .split(",");
                }
                this.optionsParams = optionsParams;
                visitChildren();
                preSearchItem.optionsParams = optionsParams;
                this.optionsParams = null;
            }
            preSearchItem.domain = node.getAttribute("domain") || "[]";
        }
        if (node.hasAttribute("invisible")) {
            preSearchItem.invisible = node.getAttribute("invisible");
            const fieldName = preSearchItem.fieldName;
            if (fieldName && !this.fields[fieldName]) {
                // In some case when a field is limited to specific groups
                // on the model, we need to ensure to discard related filter
                // as it may still be present in the view (in 'invisible' state)
                return;
            }
        }
        preSearchItem.groupNumber = this.groupNumber;
        if (node.hasAttribute("name")) {
            const name = node.getAttribute("name");
            preSearchItem.name = name;
            if (name in this.searchDefaults) {
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
        }
        if (node.hasAttribute("string")) {
            preSearchItem.description = node.getAttribute("string");
        } else if (preSearchItem.fieldName) {
            preSearchItem.description = this.fields[preSearchItem.fieldName].string;
        } else if (node.hasAttribute("help")) {
            preSearchItem.description = node.getAttribute("help");
        } else if (node.hasAttribute("name")) {
            preSearchItem.description = node.getAttribute("name");
        } else {
            preSearchItem.description = "Ω";
        }
        this.currentGroup.push(preSearchItem);
    }

    visitDateOption(node) {
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

    visitGroup(node, visitChildren) {
        this.pushGroup();
        visitChildren();
        this.pushGroup();
    }

    visitSearch(node, visitChildren) {
        visitChildren();
        this.pushGroup();
        if (this.pregroupOfGroupBys.length) {
            this.preSearchItems.push(this.pregroupOfGroupBys);
        }
    }

    visitSearchPanel(searchPanelNode) {
        let hasCategoryWithCounters = false;
        let hasFilterWithDomain = false;
        let nextSectionId = 1;

        if (searchPanelNode.hasAttribute("class")) {
            this.searchPanelInfo.className = searchPanelNode.getAttribute("class");
        }
        if (searchPanelNode.hasAttribute("view_types")) {
            this.searchPanelInfo.viewTypes = searchPanelNode.getAttribute("view_types").split(",");
        }

        for (const node of searchPanelNode.children) {
            if (node.nodeType !== 1 || node.tagName !== "field") {
                continue;
            }
            if (
                node.getAttribute("invisible") === "True" ||
                node.getAttribute("invisible") === "1"
            ) {
                continue;
            }
            const attrs = {};
            for (const attrName of node.getAttributeNames()) {
                attrs[attrName] = node.getAttribute(attrName);
            }

            const type = attrs.select === "multi" ? "filter" : "category";
            const section = {
                color: attrs.color || null,
                description: attrs.string || this.fields[attrs.name].string,
                enableCounters: evaluateBooleanExpr(attrs.enable_counters),
                expand: evaluateBooleanExpr(attrs.expand),
                fieldName: attrs.name,
                icon: attrs.icon || null,
                id: nextSectionId++,
                limit: evaluateExpr(attrs.limit || String(DEFAULT_LIMIT)),
                type,
                values: new Map(),
            };
            if (type === "category") {
                section.activeValueId = this.searchPanelDefaults[attrs.name];
                section.icon = section.icon || "fa-folder";
                section.hierarchize = evaluateBooleanExpr(attrs.hierarchize || "1");
                section.depth = attrs.depth ? parseInt(attrs.depth) : 0;
                section.values.set(false, {
                    childrenIds: [],
                    display_name: ALL.toString(),
                    id: false,
                    bold: true,
                    parentId: false,
                });
                hasCategoryWithCounters = hasCategoryWithCounters || section.enableCounters;
            } else {
                section.domain = attrs.domain || "[]";
                section.groupBy = attrs.groupby || null;
                section.icon = section.icon || "fa-filter";
                hasFilterWithDomain = hasFilterWithDomain || section.domain !== "[]";
            }
            this.sections.push([section.id, section]);
        }

        /**
         * Category counters are automatically disabled if a filter domain is found
         * to avoid inconsistencies with the counters. The underlying problem could
         * actually be solved by reworking the search panel and the way the
         * counters are computed, though this is not the current priority
         * considering the time it would take, hence this quick "fix".
         */
        if (hasCategoryWithCounters && hasFilterWithDomain) {
            // If incompatibilities are found -> disables all category counters
            for (const section of this.sections) {
                if (section.type === "category") {
                    section.enableCounters = false;
                }
            }
            // ... and triggers a warning
            console.warn(
                "Warning: categories with counters are incompatible with filters having a domain attribute.",
                "All category counters have been disabled to avoid inconsistencies."
            );
        }

        return false; // we do not want to let the parser keep visiting children
    }

    visitSeparator() {
        this.pushGroup();
    }
}
