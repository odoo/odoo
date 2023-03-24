/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { _lt } from "@web/core/l10n/translation";
import { evaluateExpr } from "@web/core/py_js/py";
import { XMLParser } from "@web/core/utils/xml";
import { DEFAULT_INTERVAL, DEFAULT_PERIOD } from "@web/search/utils/dates";

const ALL = _lt("All");
const DEFAULT_LIMIT = 200;
const DEFAULT_VIEWS_WITH_SEARCH_PANEL = ["kanban", "list"];

/**
 * Returns the split 'group_by' key from the given context attribute.
 * This helper accepts any invalid context or one that does not have
 * a valid 'group_by' key, and falls back to an empty list.
 * @param {string} context
 * @returns {string[]}
 */
function getContextGroubBy(context) {
    try {
        return makeContext([context]).group_by.split(":");
    } catch (_err) {
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

export class SearchArchParser extends XMLParser {
    constructor(searchViewDescription, fields, searchDefaults = {}, searchPanelDefaults = {}) {
        super();

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
    }

    parse() {
        this.visitXML(this.arch, (node, visitChildren) => {
            switch (node.tagName) {
                case "search":
                    this.visitSearch(node, visitChildren);
                    break;
                case "searchpanel":
                    this.visitSearchPanel(node);
                    break;
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
                    this.visitFilter(node);
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
        const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
        if (modifiers.invisible === true) {
            preField.invisible = true;
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
            preField.fieldName = name;
            preField.fieldType = this.fields[name].type;
            if (name in this.searchDefaults) {
                preField.isDefault = true;
                let value = this.searchDefaults[name];
                value = Array.isArray(value) ? value[0] : value;
                let operator = preField.operator;
                if (!operator) {
                    let type = preField.fieldType;
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
                const { fieldType, fieldName } = preField;
                const { selection, context, relation } = this.fields[fieldName];
                preField.defaultAutocompleteValue = { label: `${value}`, operator, value };
                if (fieldType === "selection") {
                    const option = selection.find((sel) => sel[0] === value);
                    if (!option) {
                        throw Error();
                    }
                    preField.defaultAutocompleteValue.label = option[1];
                } else if (fieldType === "many2one") {
                    this.labels.push((orm) => {
                        return orm.call(relation, "name_get", [value], { context }).then((results) => {
                            preField.defaultAutocompleteValue.label = results[0][1];
                        });
                    });
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

    visitFilter(node) {
        const preSearchItem = { type: "filter" };
        if (node.hasAttribute("context")) {
            const context = node.getAttribute("context");
            const [fieldName, defaultInterval] = getContextGroubBy(context);
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
                preSearchItem.defaultGeneratorIds = [DEFAULT_PERIOD];
                if (node.hasAttribute("default_period")) {
                    preSearchItem.defaultGeneratorIds = node
                        .getAttribute("default_period")
                        .split(",");
                }
            } else {
                let stringRepr = "[]";
                if (node.hasAttribute("domain")) {
                    stringRepr = node.getAttribute("domain");
                }
                preSearchItem.domain = stringRepr;
            }
        }
        const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
        if (modifiers.invisible === true) {
            preSearchItem.invisible = true;
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
                if (["groupBy", "dateGroupBy"].includes(preSearchItem.type)) {
                    const value = this.searchDefaults[name];
                    preSearchItem.defaultRank = typeof value === "number" ? value : 100;
                } else {
                    preSearchItem.defaultRank = -5;
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
            const modifiers = JSON.parse(node.getAttribute("modifiers") || "{}");
            if (modifiers.invisible === true) {
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
                enableCounters: Boolean(evaluateExpr(attrs.enable_counters || "0")),
                expand: Boolean(evaluateExpr(attrs.expand || "0")),
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
                section.hierarchize = Boolean(evaluateExpr(attrs.hierarchize || "1"));
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
