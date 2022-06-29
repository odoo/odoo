/** @odoo-module **/

import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { sortBy } from "@web/core/utils/arrays";
import { deepCopy } from "@web/core/utils/objects";
import { SearchArchParser } from "./search_arch_parser";
import {
    constructDateDomain,
    DEFAULT_INTERVAL,
    getComparisonOptions,
    getIntervalOptions,
    getPeriodOptions,
    rankInterval,
    yearSelected,
} from "./utils/dates";
import { FACET_ICONS } from "./utils/misc";

const { EventBus, toRaw } = owl;
const { DateTime } = luxon;

/**
 * @typedef {Object} ComparisonDomain
 * @property {DomainListRepr} arrayRepr
 * @property {string} description
 */

/**
 * @typedef {Object} Comparison
 * @property {ComparisonDomain[]} domains
 * @property {string} [fieldName]
 */

/**
 * @typedef {Object} SearchParams
 * @property {Comparison | null} comparison
 * @property {Context} context
 * @property {DomainListRepr} domain
 * @property {string[]} groupBy
 * @property {string[]} orderBy
 * @property {boolean} [useSampleModel] to remove?
 */

/** @todo rework doc */
// interface SectionCommon { // check optional keys
//     color: string;
//     description: string;
//     errorMsg: [string];
//     enableCounters: boolean;
//     expand: boolean;
//     fieldName: string;
//     icon: string;
//     id: number;
//     limit: number;
//     values: Map<any,any>;
//   }

//   export interface Category extends SectionCommon {
//     type: "category";
//     hierarchize: boolean;
//   }

//   export interface Filter extends SectionCommon {
//     type: "filter";
//     domain: string;
//     groupBy: string;
//     groups: Map<any,any>;
//   }

//   export type Section = Category | Filter;

//   export type SectionPredicate = (section: Section) => boolean;

/**
 * @param {Section} section
 * @returns {boolean}
 */
function hasValues(section) {
    const { errorMsg, type, values } = section;
    if (errorMsg) {
        return true;
    }
    switch (type) {
        case "category": {
            return values && values.size > 1; // false item ignored
        }
        case "filter": {
            return values && values.size > 0;
        }
    }
}

/**
 * Returns a serialised array of the given map with its values being the
 * shallow copies of the original values.
 * @param {Map<any, Object>} map
 * @return {Array[]}
 */
function mapToArray(map) {
    const result = [];
    for (const [key, val] of map) {
        const valCopy = Object.assign({}, val);
        result.push([key, valCopy]);
    }
    return result;
}
/**
 * @param {Array[]}
 * @returns {Map<any, Object>} map
 */
function arraytoMap(array) {
    return new Map(array);
}

/**
 * @param {Function} op
 * @param {Object} source
 * @param {Object} target
 */
function execute(op, source, target) {
    const {
        query,
        nextId,
        nextGroupId,
        nextGroupNumber,
        searchItems,
        searchPanelInfo,
        sections,
    } = source;

    target.nextGroupId = nextGroupId;
    target.nextGroupNumber = nextGroupNumber;
    target.nextId = nextId;

    target.query = query;
    target.searchItems = searchItems;

    target.searchPanelInfo = searchPanelInfo;

    target.sections = op(sections);
    for (const [, section] of target.sections) {
        section.values = op(section.values);
        if (section.groups) {
            section.groups = op(section.groups);
            for (const [, group] of section.groups) {
                group.values = op(group.values);
            }
        }
    }
}

//--------------------------------------------------------------------------
// Global constants/variables
//--------------------------------------------------------------------------

const FAVORITE_PRIVATE_GROUP = 1;
const FAVORITE_SHARED_GROUP = 2;

export class SearchModel extends EventBus {
    constructor(env, services) {
        super();
        this.env = env;
        this.setup(services);
    }
    /**
     * @override
     */
    setup(services) {
        // services
        const { orm, user, view } = services;
        this.orm = orm;
        this.userService = user;
        this.viewService = view;

        // used to manage search items related to date/datetime fields
        this.referenceMoment = DateTime.local();
        this.comparisonOptions = getComparisonOptions();
        this.intervalOptions = getIntervalOptions();
        this.optionGenerators = getPeriodOptions(this.referenceMoment);
    }

    /**
     *
     * @param {Object} config
     * @param {string} config.resModel
     *
     * @param {string} [config.searchViewArch="<search/>"]
     * @param {Object} [config.searchViewFields={}]
     * @param {number|false} [config.searchViewId=false]
     * @param {Object[]} [config.irFilters=[]]
     *
     * @param {boolean} [config.activateFavorite=true]
     * @param {Object | null} [config.comparison]
     * @param {Object} [config.context={}]
     * @param {Array} [config.domain=[]]
     * @param {Array} [config.dynamicFilters=[]]
     * @param {string[]} [config.groupBy=[]]
     * @param {boolean} [config.loadIrFilters=false]
     * @param {boolean} [config.display.searchPanel=true]
     * @param {string[]} [config.orderBy=[]]
     * @param {string[]} [config.searchMenuTypes=["filter", "groupBy", "favorite"]]
     * @param {Object} [config.state]
     */
    async load(config) {
        const { resModel } = config;
        if (!resModel) {
            throw Error(`SearchPanel config should have a "resModel" key`);
        }
        this.resModel = resModel;

        // used to avoid useless recomputations
        this._reset();

        const { comparison, context, domain, groupBy, orderBy } = config;

        this.globalComparison = comparison;
        this.globalContext = toRaw(context || {});
        this.globalDomain = domain || [];
        this.globalGroupBy = groupBy || [];
        this.globalOrderBy = orderBy || [];

        this.searchMenuTypes = new Set(config.searchMenuTypes || ["filter", "groupBy", "favorite"]);

        let { irFilters, loadIrFilters, searchViewArch, searchViewFields, searchViewId } = config;
        const loadSearchView =
            searchViewId !== undefined &&
            (!searchViewArch || !searchViewFields || (!irFilters && loadIrFilters));

        const searchViewDescription = {};
        if (loadSearchView) {
            const result = await this.viewService.loadViews(
                {
                    context: this.globalContext,
                    resModel,
                    views: [[searchViewId, "search"]],
                },
                {
                    actionId: this.env.config.actionId,
                    loadIrFilters: loadIrFilters || false,
                }
            );
            Object.assign(searchViewDescription, result.views.search);
            searchViewFields = searchViewFields || result.fields;
        }
        if (searchViewArch) {
            searchViewDescription.arch = searchViewArch;
        }
        if (irFilters) {
            searchViewDescription.irFilters = irFilters;
        }
        if (searchViewId !== undefined) {
            searchViewDescription.viewId = searchViewId;
        }
        this.searchViewArch = searchViewDescription.arch || "<search/>";
        this.searchViewFields = searchViewFields || {};
        if (searchViewDescription.irFilters) {
            this.irFilters = searchViewDescription.irFilters;
        }
        if (searchViewDescription.viewId !== undefined) {
            this.searchViewId = searchViewDescription.viewId;
        }

        if (config.state) {
            this._importState(config.state);
            this.__legacyParseSearchPanelArchAnyway(searchViewDescription, searchViewFields);
            this.domainParts = {};
            this.display = this._getDisplay(config.display);
            if (!this.searchPanelInfo.loaded) {
                return this._reloadSections();
            }
            return;
        }

        this.blockNotification = true;

        this.searchItems = {};
        this.query = [];

        this.nextId = 1;
        this.nextGroupId = 1;
        this.nextGroupNumber = 1;

        // ... to rework (API for external domain, groupBy, facet)
        this.domainParts = {}; // put in state?

        const searchDefaults = {};
        const searchPanelDefaults = {};

        for (const key in this.globalContext) {
            const defaultValue = this.globalContext[key];
            const searchDefaultMatch = /^search_default_(.*)$/.exec(key);
            if (searchDefaultMatch) {
                if (defaultValue) {
                    searchDefaults[searchDefaultMatch[1]] = defaultValue;
                }
                delete this.globalContext[key];
                continue;
            }
            const searchPanelDefaultMatch = /^searchpanel_default_(.*)$/.exec(key);
            if (searchPanelDefaultMatch) {
                searchPanelDefaults[searchPanelDefaultMatch[1]] = defaultValue;
                delete this.globalContext[key];
            }
        }

        const parser = new SearchArchParser(
            searchViewDescription,
            searchViewFields,
            searchDefaults,
            searchPanelDefaults
        );
        const { labels, preSearchItems, searchPanelInfo, sections } = parser.parse();

        this.searchPanelInfo = { ...searchPanelInfo, loaded: false, shouldReload: false };

        await Promise.all(labels.map((cb) => cb(this.orm)));

        // prepare search items (populate this.searchItems)
        for (const preGroup of preSearchItems || []) {
            this._createGroupOfSearchItems(preGroup);
        }
        this.nextGroupNumber =
            1 + Math.max(...Object.values(this.searchItems).map((i) => i.groupNumber || 0), 0);

        const dateFilters = Object.values(this.searchItems).filter(
            (searchElement) => searchElement.type === "dateFilter"
        );
        if (dateFilters.length) {
            this._createGroupOfComparisons(dateFilters);
        }

        const { dynamicFilters } = config;
        if (dynamicFilters) {
            this._createGroupOfDynamicFilters(dynamicFilters);
        }

        const defaultFavoriteId = this._createGroupOfFavorites(this.irFilters || []);
        const activateFavorite = "activateFavorite" in config ? config.activateFavorite : true;

        // activate default search items (populate this.query)
        this._activateDefaultSearchItems(activateFavorite ? defaultFavoriteId : null);

        // prepare search panel sections

        /** @type Map<number,Section> */
        this.sections = new Map(sections || []);
        this.display = this._getDisplay(config.display);

        if (this.display.searchPanel) {
            /** @type DomainListRepr */
            this.searchDomain = this._getDomain({ withSearchPanel: false });
            this.sectionsPromise = this._fetchSections(this.categories, this.filters).then(() => {
                for (const { fieldName, values } of this.filters) {
                    const filterDefaults = searchPanelDefaults[fieldName] || [];
                    for (const valueId of filterDefaults) {
                        const value = values.get(valueId);
                        if (value) {
                            value.checked = true;
                        }
                    }
                }
            });
            if (Object.keys(searchPanelDefaults).length || this._shouldWaitForData(false)) {
                await this.sectionsPromise;
            }
        }

        this.blockNotification = false;
    }

    /**
     * @param {Object} [config={}]
     * @param {Object | null} [config.comparison]
     * @param {Object} [config.context={}]
     * @param {Array} [config.domain=[]]
     * @param {string[]} [config.groupBy=[]]
     * @param {string[]} [config.orderBy=[]]
     */
    async reload(config = {}) {
        this._reset();

        const { comparison, context, domain, groupBy, orderBy } = config;

        this.globalContext = context || {};
        this.globalDomain = domain || [];
        this.globalComparison = comparison;
        this.globalGroupBy = groupBy || [];
        this.globalOrderBy = orderBy || [];

        await this._reloadSections();
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    /**
     * @returns {Category[]}
     */
    get categories() {
        return [...this.sections.values()].filter((s) => s.type === "category");
    }

    /**
     * @returns {Context} should be imported from context.js?
     */
    get context() {
        if (!this._context) {
            this._context = makeContext([this._getContext(), this.globalContext]);
        }
        return deepCopy(this._context);
    }

    /**
     * @returns {DomainListRepr} should be imported from domain.js?
     */
    get domain() {
        if (!this._domain) {
            this._domain = this._getDomain();
        }
        return deepCopy(this._domain);
    }

    /**
     * @returns {Comparison}
     */
    get comparison() {
        if (!this.searchMenuTypes.has("comparison")) {
            return null;
        }
        if (this._comparison === undefined) {
            if (this.globalComparison) {
                this._comparison = this.globalComparison;
            } else {
                const comparison = this.getFullComparison();
                if (comparison) {
                    const {
                        fieldName,
                        range,
                        rangeDescription,
                        comparisonRange,
                        comparisonRangeDescription,
                    } = comparison;
                    const domains = [
                        {
                            arrayRepr: Domain.and([this.domain, range]).toList(),
                            description: rangeDescription,
                        },
                        {
                            arrayRepr: Domain.and([this.domain, comparisonRange]).toList(),
                            description: comparisonRangeDescription,
                        },
                    ];
                    this._comparison = { domains, fieldName };
                } else {
                    this._comparison = null;
                }
            }
        }
        return deepCopy(this._comparison);
    }

    get facets() {
        const isValidType = (type) =>
            !["groupBy", "comparison"].includes(type) || this.searchMenuTypes.has(type);
        const facets = [];
        for (const facet of this._getFacets()) {
            if (!isValidType(facet.type)) {
                continue;
            }
            facets.push(facet);
        }
        return facets;
    }

    /**
     * @returns {Filter[]}
     */
    get filters() {
        return [...this.sections.values()].filter((s) => s.type === "filter");
    }

    /**
     * @returns {string[]}
     */
    get groupBy() {
        if (!this._groupBy) {
            this._groupBy = this._getGroupBy();
        }
        return deepCopy(this._groupBy);
    }

    /**
     * @returns {string[]}
     */
    get orderBy() {
        if (!this._orderBy) {
            this._orderBy = this._getOrderBy();
        }
        return deepCopy(this._orderBy);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Activate a filter of type 'field' with given filterId with
     * 'autocompleteValues' value, label, and operator.
     * @param {Object}
     */
    addAutoCompletionValues(searchItemId, autocompleteValue) {
        const searchItem = this.searchItems[searchItemId];
        if (searchItem.type !== "field") {
            return;
        }
        const { label, value, operator } = autocompleteValue;
        const queryElem = this.query.find(
            (queryElem) =>
                queryElem.searchItemId === searchItemId &&
                "autocompleteValue" in queryElem &&
                queryElem.autocompleteValue.value === value &&
                queryElem.autocompleteValue.operator === operator
        );
        if (!queryElem) {
            this.query.push({ searchItemId, autocompleteValue });
        } else {
            queryElem.autocompleteValue.label = label; // seems related to old stuff --> should be useless now
        }
        this._notify();
    }

    /**
     * Remove all the query elements from query.
     */
    clearQuery() {
        this.query = [];
        this._notify();
    }

    /**
     * Create a new filter of type 'favorite' and activate it.
     * A new group containing only that filter is created.
     * The query is emptied before activating the new favorite.
     * @param {Object} params
     * @returns {Promise}
     */
    async createNewFavorite(params) {
        const { preFavorite, irFilter } = this._getIrFilterDescription(params);
        const serverSideId = await this.orm.call("ir.filters", "create_or_replace", [irFilter]);
        this.env.bus.trigger("CLEAR-CACHES");

        // before the filter cache was cleared!
        this.blockNotification = true;
        this.clearQuery();
        const favorite = {
            ...preFavorite,
            type: "favorite",
            id: this.nextId,
            groupId: this.nextGroupId,
            groupNumber: preFavorite.userId ? FAVORITE_PRIVATE_GROUP : FAVORITE_SHARED_GROUP,
            removable: true,
            serverSideId,
        };
        this.searchItems[this.nextId] = favorite;
        this.query.push({ searchItemId: this.nextId });
        this.nextGroupId++;
        this.nextId++;
        this.blockNotification = false;
        this._notify();
    }

    /**
     * Create new search items of type 'filter' and activate them.
     * A new group containing only those filters is created.
     */
    createNewFilters(prefilters) {
        if (!prefilters.length) {
            return [];
        }
        prefilters.forEach((preFilter) => {
            const filter = Object.assign(preFilter, {
                groupId: this.nextGroupId,
                groupNumber: this.nextGroupNumber,
                id: this.nextId,
                type: "filter",
            });
            this.searchItems[this.nextId] = filter;
            this.query.push({ searchItemId: this.nextId });
            this.nextId++;
        });
        this.nextGroupId++;
        this.nextGroupNumber++;
        this._notify();
    }

    /**
     * Create a new filter of type 'groupBy' or 'dateGroupBy' and activate it.
     * It is added to the unique group of groupbys.
     * @param {string} fieldName
     */
    createNewGroupBy(fieldName) {
        const field = this.searchViewFields[fieldName];
        const { string, type: fieldType } = field;
        const firstGroupBy = Object.values(this.searchItems).find((f) => f.type === "groupBy");
        const preSearchItem = {
            description: string || fieldName,
            fieldName,
            fieldType,
            groupId: firstGroupBy ? firstGroupBy.groupId : this.nextGroupId++,
            groupNumber: this.nextGroupNumber,
            id: this.nextId,
            custom: true,
        };
        if (["date", "datetime"].includes(fieldType)) {
            this.searchItems[this.nextId] = Object.assign(
                { type: "dateGroupBy", defaultIntervalId: DEFAULT_INTERVAL },
                preSearchItem
            );
            this.toggleDateGroupBy(this.nextId);
        } else {
            this.searchItems[this.nextId] = Object.assign({ type: "groupBy" }, preSearchItem);
            this.toggleSearchItem(this.nextId);
        }
        this.nextGroupNumber++; // FIXME: with this, all subsequent added groups are in different groups (visually)
        this.nextId++;
        this._notify();
    }

    /**
     * Deactivate a group with provided groupId, i.e. delete the query elements
     * with given groupId.
     */
    deactivateGroup(groupId) {
        this.query = this.query.filter((queryElem) => {
            const searchItem = this.searchItems[queryElem.searchItemId];
            return searchItem.groupId !== groupId;
        });

        for (const partName in this.domainParts) {
            const part = this.domainParts[partName];
            if (part.groupId === groupId) {
                this.setDomainParts({ [partName]: null });
            }
        }
        this._checkComparisonStatus();
        this._notify();
    }

    /**
     * Delete a filter of type 'favorite' with given this.nextId server side and
     * in control panel model. Of course the filter is also removed
     * from the search query.
     */
    async deleteFavorite(favoriteId) {
        const searchItem = this.searchItems[favoriteId];
        if (searchItem.type !== "favorite") {
            return;
        }
        const { serverSideId } = searchItem;
        await this.orm.unlink("ir.filters", [serverSideId]);
        this.env.bus.trigger("CLEAR-CACHES");
        const index = this.query.findIndex((queryElem) => queryElem.searchItemId === favoriteId);
        delete this.searchItems[favoriteId];
        if (index >= 0) {
            this.query.splice(index, 1);
        }
        this._notify();
    }

    /**
     * @returns {Object}
     */
    exportState() {
        const state = {};
        execute(mapToArray, this, state);
        return state;
    }

    getDomainPart(partName) {
        let part = this.domainParts[partName] || null;
        if (part) {
            return deepCopy(part);
        }
        return part;
    }

    getDomainParts() {
        const copy = deepCopy(this.domainParts);
        return sortBy(Object.values(copy), (part) => part.groupId);
    }

    getFullComparison() {
        let searchItem = null;
        for (const queryElem of this.query.slice().reverse()) {
            const item = this.searchItems[queryElem.searchItemId];
            if (item.type === "comparison") {
                searchItem = item;
                break;
            } else if (item.type === "favorite" && item.comparison) {
                searchItem = item;
                break;
            }
        }
        if (!searchItem) {
            return null;
        } else if (searchItem.type === "favorite") {
            return searchItem.comparison;
        }
        const { dateFilterId, comparisonOptionId } = searchItem;
        const { fieldName, fieldType, description: dateFilterDescription } = this.searchItems[
            dateFilterId
        ];
        const selectedGeneratorIds = this._getSelectedGeneratorIds(dateFilterId);
        // compute range and range description
        const { domain: range, description: rangeDescription } = constructDateDomain(
            this.referenceMoment,
            fieldName,
            fieldType,
            selectedGeneratorIds
        );
        // compute comparisonRange and comparisonRange description
        const {
            domain: comparisonRange,
            description: comparisonRangeDescription,
        } = constructDateDomain(
            this.referenceMoment,
            fieldName,
            fieldType,
            selectedGeneratorIds,
            comparisonOptionId
        );
        return {
            comparisonId: comparisonOptionId,
            fieldName,
            fieldDescription: dateFilterDescription,
            range: range.toList(),
            rangeDescription,
            comparisonRange: comparisonRange.toList(),
            comparisonRangeDescription,
        };
    }

    getIrFilterValues(params) {
        const { irFilter } = this._getIrFilterDescription(params);
        return irFilter;
    }

    /**
     * Return an array containing enriched copies of all searchElements or of those
     * satifying the given predicate if any
     * @param {Function} [predicate]
     * @returns {Object[]}
     */
    getSearchItems(predicate) {
        const searchItems = [];
        Object.values(this.searchItems).forEach((searchItem) => {
            if (
                (!("invisible" in searchItem) || !searchItem.invisible) &&
                (!predicate || predicate(searchItem))
            ) {
                const enrichedSearchitem = this._enrichItem(searchItem);
                if (enrichedSearchitem) {
                    searchItems.push(enrichedSearchitem);
                }
            }
        });
        if (searchItems.some((f) => f.type === "favorite")) {
            searchItems.sort((f1, f2) => f1.groupNumber - f2.groupNumber);
        }
        return searchItems;
    }

    /**
     * Returns a sorted list of a copy of all sections. This list can be
     * filtered by a given predicate.
     * @param {SectionPredicate} [predicate] used to determine
     *      which subsets of sections is wanted
     * @returns {Section[]}
     */
    getSections(predicate) {
        let sections = [...this.sections.values()].map((section) =>
            Object.assign({}, section, { empty: !hasValues(section) })
        );
        if (predicate) {
            sections = sections.filter(predicate);
        }
        return sections.sort((s1, s2) => s1.index - s2.index);
    }

    search() {
        this.trigger("update");
    }

    setDomainParts(parts) {
        for (const key in parts) {
            const val = parts[key];

            if (!val) {
                delete this.domainParts[key];
            } else {
                this.domainParts[key] = val;
                val.groupId = this.nextGroupId++;
            }
        }
        this._notify();
    }

    /**
     * Set the active value id of a given category.
     * @param {number} sectionId
     * @param {number} valueId
     */
    toggleCategoryValue(sectionId, valueId) {
        const category = this.sections.get(sectionId);
        category.activeValueId = valueId;
        this._notify();
    }

    /**
     * Toggle a filter value of a given section. The value will be set
     * to "forceTo" if provided, else it will be its own opposed value.
     * @param {number} sectionId
     * @param {number[]} valueIds
     * @param {boolean} [forceTo=null]
     */
    toggleFilterValues(sectionId, valueIds, forceTo = null) {
        const filter = this.sections.get(sectionId);
        for (const valueId of valueIds) {
            const value = filter.values.get(valueId);
            value.checked = forceTo === null ? !value.checked : forceTo;
        }
        this._notify();
    }

    /**
     * Activate or deactivate the simple filter with given filterId, i.e.
     * add or remove a corresponding query element.
     */
    toggleSearchItem(searchItemId) {
        const searchItem = this.searchItems[searchItemId];
        switch (searchItem.type) {
            case "dateFilter":
            case "dateGroupBy":
            case "field": {
                return;
            }
        }
        const index = this.query.findIndex((queryElem) => queryElem.searchItemId === searchItemId);
        if (index >= 0) {
            this.query.splice(index, 1);
        } else {
            if (searchItem.type === "favorite") {
                this.query = [];
            } else if (searchItem.type === "comparison") {
                // make sure only one comparison can be active
                this.query = this.query.filter((queryElem) => {
                    const { type } = this.searchItems[queryElem.searchItemId];
                    return type !== "comparison";
                });
            }
            this.query.push({ searchItemId });
        }
        this._notify();
    }

    /**
     * Used to toggle a query element.
     * This can impact the query in various form, e.g. add/remove other query elements
     * in case the filter is of type 'filter'.
     */
    toggleDateFilter(searchItemId, generatorId) {
        const searchItem = this.searchItems[searchItemId];
        if (searchItem.type !== "dateFilter") {
            return;
        }
        generatorId = generatorId || searchItem.defaultGeneratorId;
        const index = this.query.findIndex(
            (queryElem) =>
                queryElem.searchItemId === searchItemId &&
                "generatorId" in queryElem &&
                queryElem.generatorId === generatorId
        );
        if (index >= 0) {
            this.query.splice(index, 1);
            if (!yearSelected(this._getSelectedGeneratorIds(searchItemId))) {
                // This is the case where generatorId was the last option
                // of type 'year' to be there before being removed above.
                // Since other options of type 'month' or 'quarter' do
                // not make sense without a year we deactivate all options.
                this.query = this.query.filter(
                    (queryElem) => queryElem.searchItemId !== searchItemId
                );
            }
        } else {
            this.query.push({ searchItemId, generatorId });
            if (!yearSelected(this._getSelectedGeneratorIds(searchItemId))) {
                // Here we add 'this_year' as options if no option of type
                // year is already selected.
                const { defaultYearId } = this.optionGenerators.find((o) => o.id === generatorId);
                this.query.push({ searchItemId, generatorId: defaultYearId });
            }
        }
        this._checkComparisonStatus();
        this._notify();
    }

    toggleDateGroupBy(searchItemId, intervalId) {
        const searchItem = this.searchItems[searchItemId];
        if (searchItem.type !== "dateGroupBy") {
            return;
        }
        intervalId = intervalId || searchItem.defaultIntervalId;
        const index = this.query.findIndex(
            (queryElem) =>
                queryElem.searchItemId === searchItemId &&
                "intervalId" in queryElem &&
                queryElem.intervalId === intervalId
        );
        if (index >= 0) {
            this.query.splice(index, 1);
        } else {
            this.query.push({ searchItemId, intervalId });
        }
        this._notify();
    }

    //--------------------------------------------------------------------------
    // Private methods
    //--------------------------------------------------------------------------

    /**
     * Activate the default favorite (if any) or all default filters.
     */
    _activateDefaultSearchItems(defaultFavoriteId) {
        if (defaultFavoriteId) {
            // Activate default favorite
            this.toggleSearchItem(defaultFavoriteId);
        } else {
            // Activate default filters
            Object.values(this.searchItems)
                .filter((f) => f.isDefault && f.type !== "favorite")
                .sort((f1, f2) => (f1.defaultRank || 100) - (f2.defaultRank || 100))
                .forEach((f) => {
                    if (f.type === "dateFilter") {
                        this.toggleDateFilter(f.id);
                    } else if (f.type === "dateGroupBy") {
                        this.toggleDateGroupBy(f.id);
                    } else if (f.type === "field") {
                        this.addAutoCompletionValues(f.id, f.defaultAutocompleteValue);
                    } else {
                        this.toggleSearchItem(f.id);
                    }
                });
        }
    }

    /**
     * If a comparison is active, check if it should become inactive.
     * The comparison should become inactive if the corresponding date filter has become
     * inactive.
     */
    _checkComparisonStatus() {
        const activeComparison = this._getActiveComparison();
        if (!activeComparison) {
            return;
        }
        const { dateFilterId, id } = activeComparison;
        const dateFilterIsActive = this.query.some(
            (queryElem) => queryElem.searchItemId === dateFilterId
        );
        if (!dateFilterIsActive) {
            this.query = this.query.filter((queryElem) => queryElem.searchItemId !== id);
        }
    }

    /**
     * @param {string} sectionId
     * @param {Object} result
     */
    _createCategoryTree(sectionId, result) {
        const category = this.sections.get(sectionId);

        let { error_msg, parent_field: parentField, values } = result;
        if (error_msg) {
            category.errorMsg = error_msg;
            values = [];
        }
        if (category.hierarchize) {
            category.parentField = parentField;
        }
        for (const value of values) {
            category.values.set(
                value.id,
                Object.assign({}, value, {
                    childrenIds: [],
                    parentId: value[parentField] || false,
                })
            );
        }
        for (const value of values) {
            const { parentId } = category.values.get(value.id);
            if (parentId && category.values.has(parentId)) {
                category.values.get(parentId).childrenIds.push(value.id);
            }
        }
        // collect rootIds
        category.rootIds = [false];
        for (const value of values) {
            const { parentId } = category.values.get(value.id);
            if (!parentId) {
                category.rootIds.push(value.id);
            }
        }
        // Set active value from context
        const valueIds = [false, ...values.map((val) => val.id)];
        this._ensureCategoryValue(category, valueIds);
    }

    /**
     * @param {string} sectionId
     * @param {Object} result
     */
    _createFilterTree(sectionId, result) {
        const filter = this.sections.get(sectionId);

        let { error_msg, values } = result;
        if (error_msg) {
            filter.errorMsg = error_msg;
            values = [];
        }

        // restore checked property
        values.forEach((value) => {
            const oldValue = filter.values.get(value.id);
            value.checked = oldValue ? oldValue.checked : false;
        });

        filter.values = new Map();
        const groupIds = [];
        if (filter.groupBy) {
            const groups = new Map();
            for (const value of values) {
                const groupId = value.group_id;
                if (!groups.has(groupId)) {
                    if (groupId) {
                        groupIds.push(groupId);
                    }
                    groups.set(groupId, {
                        id: groupId,
                        name: value.group_name,
                        values: new Map(),
                        tooltip: value.group_tooltip,
                        sequence: value.group_sequence,
                        hex_color: value.group_hex_color,
                    });
                    // restore former checked state
                    const oldGroup = filter.groups && filter.groups.get(groupId);
                    groups.get(groupId).state = (oldGroup && oldGroup.state) || false;
                }
                groups.get(groupId).values.set(value.id, value);
            }
            filter.groups = groups;
            filter.sortedGroupIds = sortBy(
                groupIds,
                (id) => groups.get(id).sequence || groups.get(id).name
            );
            for (const group of filter.groups.values()) {
                for (const [valueId, value] of group.values) {
                    filter.values.set(valueId, value);
                }
            }
        } else {
            for (const value of values) {
                filter.values.set(value.id, value);
            }
        }
    }

    /**
     * Starting from the array of date filters, create the filters of type
     * 'comparison'.
     * @param {Object[]} dateFilters
     */
    _createGroupOfComparisons(dateFilters) {
        const preSearchItem = [];
        for (const dateFilter of dateFilters) {
            for (const comparisonOption of this.comparisonOptions) {
                const { id: dateFilterId, description } = dateFilter;
                const preFilter = {
                    type: "comparison",
                    comparisonOptionId: comparisonOption.id,
                    description: `${description}: ${comparisonOption.description}`,
                    dateFilterId,
                };
                preSearchItem.push(preFilter);
            }
        }
        this._createGroupOfSearchItems(preSearchItem);
    }

    /**
     * Add filters of type 'filter' determined by the key array dynamicFilters.
     */
    _createGroupOfDynamicFilters(dynamicFilters) {
        const pregroup = dynamicFilters.map((filter) => {
            return {
                groupNumber: this.nextGroupNumber,
                description: filter.description,
                domain: filter.domain,
                isDefault: true,
                type: "filter",
            };
        });
        this.nextGroupNumber++;
        this._createGroupOfSearchItems(pregroup);
    }

    /**
     * Add filters of type 'favorite' determined by the array this.favoriteFilters.
     */
    _createGroupOfFavorites(irFilters) {
        let defaultFavoriteId = null;
        irFilters.forEach((irFilter) => {
            const favorite = this._irFilterToFavorite(irFilter);
            this._createGroupOfSearchItems([favorite]);
            if (favorite.isDefault) {
                defaultFavoriteId = favorite.id;
            }
        });
        return defaultFavoriteId;
    }

    /**
     * Using a list (a 'pregroup') of 'prefilters', create new filters in `searchItems`
     * for each prefilter. The new filters belong to a same new group.
     */
    _createGroupOfSearchItems(pregroup) {
        pregroup.forEach((preSearchItem) => {
            const searchItem = Object.assign(preSearchItem, {
                groupId: this.nextGroupId,
                id: this.nextId,
            });
            this.searchItems[this.nextId] = searchItem;
            this.nextId++;
        });
        this.nextGroupId++;
    }

    /**
     * Returns null or a copy of the provided filter with additional information
     * used only outside of the control panel model, like in search bar or in the
     * various menus. The value null is returned if the filter should not appear
     * for some reason.
     */
    _enrichItem(searchItem) {
        const queryElements = this.query.filter(
            (queryElem) => queryElem.searchItemId === searchItem.id
        );
        const isActive = Boolean(queryElements.length);
        const enrichSearchItem = Object.assign({ isActive }, searchItem);
        function _enrichOptions(options, selectedIds) {
            return options.map((o) => {
                const { description, id, groupNumber } = o;
                const isActive = selectedIds.some((optionId) => optionId === id);
                return { description, id, groupNumber, isActive };
            });
        }
        switch (searchItem.type) {
            case "comparison": {
                const { dateFilterId } = searchItem;
                const dateFilterIsActive = this.query.some(
                    (queryElem) => queryElem.searchItemId === dateFilterId
                );
                if (!dateFilterIsActive) {
                    return null;
                }
                break;
            }
            case "dateFilter":
                enrichSearchItem.options = _enrichOptions(
                    this.optionGenerators,
                    queryElements.map((queryElem) => queryElem.generatorId)
                );
                break;
            case "dateGroupBy":
                enrichSearchItem.options = _enrichOptions(
                    this.intervalOptions,
                    queryElements.map((queryElem) => queryElem.intervalId)
                );
                break;
            case "field":
                enrichSearchItem.autocompleteValues = queryElements.map(
                    (queryElem) => queryElem.autocompleteValue
                );
                break;
        }
        return enrichSearchItem;
    }

    /**
     * Ensures that the active value of a category is one of its own
     * existing values.
     * @param {Category} category
     * @param {number[]} valueIds
     */
    _ensureCategoryValue(category, valueIds) {
        if (!valueIds.includes(category.activeValueId)) {
            category.activeValueId = valueIds[0];
        }
    }

    /**
     * Fetches values for each category at startup. At reload a category is
     * only fetched if needed.
     * @param {Category[]} categories
     * @returns {Promise} resolved when all categories have been fetched
     */
    async _fetchCategories(categories) {
        const filterDomain = this._getFilterDomain();
        const searchDomain = this.searchDomain;
        await Promise.all(
            categories.map(async (category) => {
                const result = await this.orm.call(
                    this.resModel,
                    "search_panel_select_range",
                    [category.fieldName],
                    {
                        category_domain: this._getCategoryDomain(category.id),
                        enable_counters: category.enableCounters,
                        expand: category.expand,
                        filter_domain: filterDomain,
                        hierarchize: category.hierarchize,
                        limit: category.limit,
                        search_domain: searchDomain,
                    }
                );
                this._createCategoryTree(category.id, result);
            })
        );
    }

    /**
     * Fetches values for each filter. This is done at startup and at each
     * reload if needed.
     * @param {Filter[]} filters
     * @returns {Promise} resolved when all filters have been fetched
     */
    async _fetchFilters(filters) {
        const evalContext = {};
        for (const category of this.categories) {
            evalContext[category.fieldName] = category.activeValueId;
        }
        const categoryDomain = this._getCategoryDomain();
        const searchDomain = this.searchDomain;
        await Promise.all(
            filters.map(async (filter) => {
                const result = await this.orm.call(
                    this.resModel,
                    "search_panel_select_multi_range",
                    [filter.fieldName],
                    {
                        category_domain: categoryDomain,
                        comodel_domain: new Domain(filter.domain).toList(evalContext),
                        enable_counters: filter.enableCounters,
                        filter_domain: this._getFilterDomain(filter.id),
                        expand: filter.expand,
                        group_by: filter.groupBy || false,
                        group_domain: this._getGroupDomain(filter),
                        limit: filter.limit,
                        search_domain: searchDomain,
                    }
                );
                this._createFilterTree(filter.id, result);
            })
        );
    }

    /**
     * Fetches values for the given categories and filters.
     * @param {Category[]} categoriesToLoad
     * @param {Filter[]} filtersToLoad
     * @returns {Promise} resolved when all categories have been fetched
     */
    async _fetchSections(categoriesToLoad, filtersToLoad) {
        await this._fetchCategories(categoriesToLoad);
        await this._fetchFilters(filtersToLoad);
        this.searchPanelInfo.loaded = true;
    }

    _getActiveComparison() {
        for (const queryElem of this.query) {
            const searchItem = this.searchItems[queryElem.searchItemId];
            if (searchItem.type === "comparison") {
                return searchItem;
            }
        }
        return null;
    }

    /**
     * Computes and returns the domain based on the current active
     * categories. If "excludedCategoryId" is provided, the category with
     * that id is not taken into account in the domain computation.
     * @param {string} [excludedCategoryId]
     * @returns {Array[]}
     */
    _getCategoryDomain(excludedCategoryId) {
        const domain = [];
        for (const category of this.categories) {
            if (category.id === excludedCategoryId || !category.activeValueId) {
                continue;
            }
            const field = this.searchViewFields[category.fieldName];
            const operator = field.type === "many2one" && category.parentField ? "child_of" : "=";
            domain.push([category.fieldName, operator, category.activeValueId]);
        }
        return domain;
    }

    /**
     * Construct a single context from the contexts of
     * filters of type 'filter', 'favorite', and 'field'.
     * @returns {Object}
     */
    _getContext() {
        const groups = this._getGroups();
        const contexts = [this.userService.context];
        for (const group of groups) {
            for (const activeItem of group.activeItems) {
                const context = this._getSearchItemContext(activeItem);
                if (context) {
                    contexts.push(context);
                }
            }
        }
        let context;
        try {
            context = makeContext(contexts);
            return context;
        } catch (error) {
            throw new Error(
                `${this.env._t("Failed to evaluate the context")} ${context}.\n${error.message}`
            );
        }
    }

    /**
     * Compute the string representation or the description of the current domain associated
     * with a date filter starting from its corresponding query elements.
     */
    _getDateFilterDomain(dateFilter, generatorIds, key = "domain") {
        const { fieldName, fieldType } = dateFilter;
        const dateFilterRange = constructDateDomain(
            this.referenceMoment,
            fieldName,
            fieldType,
            generatorIds
        );
        return dateFilterRange[key];
    }

    /**
     * Returns which components are displayed in the current action. Components
     * are opt-out, meaning that they will be displayed as long as a falsy
     * value is not provided. With the search panel, the view type must also
     * match the given (or default) search panel view types if the search model
     * is instanciated in a view (this doesn't apply for any other action type).
     * @private
     * @param {Object} [display={}]
     * @returns {{ controlPanel: Object | false, searchPanel: boolean }}
     */
    _getDisplay(display = {}) {
        const { viewTypes } = this.searchPanelInfo;
        const { bannerRoute, viewType } = this.env.config;
        return {
            controlPanel: "controlPanel" in display ? display.controlPanel : {},
            searchPanel:
                this.sections.size &&
                (!viewType || viewTypes.includes(viewType)) &&
                ("searchPanel" in display ? display.searchPanel : true),
            banner: Boolean(bannerRoute),
        };
    }

    /**
     * Return a domain created by combinining appropriately (with an 'AND') the domains
     * coming from the active groups of type 'filter', 'dateFilter', 'favorite', and 'field'.
     * @param {Object} [params]
     * @param {boolean} [params.raw=false]
     * @param {boolean} [params.withSearchPanel=true]
     * @param {boolean} [params.withGlobal=true]
     * @returns {DomainListRepr | Domain} Domain instance if 'raw', else the evaluated list domain
     */
    _getDomain(params = {}) {
        const withSearchPanel = "withSearchPanel" in params ? params.withSearchPanel : true;
        const withGlobal = "withGlobal" in params ? params.withGlobal : true;

        const groups = this._getGroups();
        const domains = [];
        if (withGlobal) {
            domains.push(this.globalDomain);
        }
        for (const group of groups) {
            const groupActiveItemDomains = [];
            for (const activeItem of group.activeItems) {
                const domain = this._getSearchItemDomain(activeItem);
                if (domain) {
                    groupActiveItemDomains.push(domain);
                }
            }
            const groupDomain = Domain.or(groupActiveItemDomains);
            domains.push(groupDomain);
        }

        for (const { domain } of this.getDomainParts()) {
            domains.push(domain);
        }
        // we need to manage (optional) facets, deactivateGroup, clearQuery,...

        if (this.display.searchPanel && withSearchPanel) {
            domains.push(this._getSearchPanelDomain());
        }

        let domain;
        try {
            domain = Domain.and(domains);
            return params.raw
                ? domain
                : domain.toList(Object.assign({}, this.globalContext, this.userService.context));
        } catch (error) {
            throw new Error(
                `${this.env._t("Failed to evaluate the domain")} ${domain.toString()}.\n${
                    error.message
                }`
            );
        }
    }

    _getFacets() {
        const facets = [];
        const groups = this._getGroups();
        for (const group of groups) {
            const values = [];
            let title;
            let type;
            for (const activeItem of group.activeItems) {
                const searchItem = this.searchItems[activeItem.searchItemId];
                switch (searchItem.type) {
                    case "field": {
                        type = "field";
                        title = searchItem.description;
                        for (const autocompleteValue of activeItem.autocompletValues) {
                            values.push(autocompleteValue.label);
                        }
                        break;
                    }
                    case "groupBy": {
                        type = "groupBy";
                        values.push(searchItem.description);
                        break;
                    }
                    case "dateGroupBy": {
                        type = "groupBy";
                        for (const intervalId of activeItem.intervalIds) {
                            const option = this.intervalOptions.find((o) => o.id === intervalId);
                            values.push(`${searchItem.description}: ${option.description}`);
                        }
                        break;
                    }
                    case "dateFilter": {
                        type = "filter";
                        const periodDescription = this._getDateFilterDomain(
                            searchItem,
                            activeItem.generatorIds,
                            "description"
                        );
                        values.push(`${searchItem.description}: ${periodDescription}`);
                        break;
                    }
                    default: {
                        type = searchItem.type;
                        values.push(searchItem.description);
                    }
                }
            }
            const facet = {
                groupId: group.id,
                type: type,
                values,
                separator: type === "groupBy" ? ">" : this.env._t("or"),
            };
            if (type === "field") {
                facet.title = title;
            } else {
                facet.icon = FACET_ICONS[type];
            }
            facets.push(facet);
        }

        for (const { facetLabel, groupId } of this.getDomainParts()) {
            const type = "filter";
            facets.push({
                groupId,
                type,
                values: [facetLabel],
                icon: FACET_ICONS[type],
            });
        }

        return facets;
    }

    /**
     * Return the domain resulting from the combination of the autocomplete values
     * of a search item of type 'field'.
     */
    _getFieldDomain(field, autocompleteValues) {
        const domains = autocompleteValues.map(({ label, value, operator }) => {
            let domain;
            if (field.filterDomain) {
                domain = new Domain(field.filterDomain).toList({
                    self: label.trim(),
                    raw_value: value,
                });
            } else {
                domain = [[field.fieldName, operator, value]];
            }
            return new Domain(domain);
        });
        return Domain.or(domains);
    }

    /**
     * Computes and returns the domain based on the current checked
     * filters. The values of a single filter are combined using a simple
     * rule: checked values within a same group are combined with an "OR"
     * operator (this is expressed as single condition using a list) and
     * groups are combined with an "AND" operator (expressed by
     * concatenation of conditions).
     * If a filter has no group, its checked values are implicitely
     * considered as forming a group (and grouped using an "OR").
     * If excludedFilterId is provided, the filter with that id is not
     * taken into account in the domain computation.
     * @param {string} [excludedFilterId]
     * @returns {Array[]}
     */
    _getFilterDomain(excludedFilterId) {
        const domain = [];

        function addCondition(fieldName, valueMap) {
            const ids = [];
            for (const [valueId, value] of valueMap) {
                if (value.checked) {
                    ids.push(valueId);
                }
            }
            if (ids.length) {
                domain.push([fieldName, "in", ids]);
            }
        }

        for (const filter of this.filters) {
            if (filter.id === excludedFilterId) {
                continue;
            }
            const { fieldName, groups, values } = filter;
            if (groups) {
                for (const group of groups.values()) {
                    addCondition(fieldName, group.values);
                }
            } else {
                addCondition(fieldName, values);
            }
        }
        return domain;
    }

    /**
     * Return the concatenation of groupBys comming from the active filters of
     * type 'favorite' and 'groupBy'.
     * The result respects the appropriate logic: the groupBys
     * coming from an active favorite (if any) come first, then come the
     * groupBys comming from the active filters of type 'groupBy' in the order
     * defined in this.query. If no groupBys are found, one tries to
     * find some grouBys in this.globalContext.
     */
    _getGroupBy() {
        const groups = this._getGroups();
        const groupBys = [];
        for (const group of groups) {
            for (const activeItem of group.activeItems) {
                const activeItemGroupBys = this._getSearchItemGroupBys(activeItem);
                if (activeItemGroupBys) {
                    groupBys.push(...activeItemGroupBys);
                }
            }
        }
        const groupBy = groupBys.length ? groupBys : this.globalGroupBy.slice();
        return typeof groupBy === "string" ? [groupBy] : groupBy;
    }

    /**
     * Returns a domain or an object of domains used to complement
     * the filter domains to accurately describe the constrains on
     * records when computing record counts associated to the filter
     * values (if a groupBy is provided). The idea is that the checked
     * values within a group should not impact the counts for the other
     * values in the same group.
     * @param {Filter} filter
     * @returns {Object<string, Array[]> | Array[] | null}
     */
    _getGroupDomain(filter) {
        const { fieldName, groups, enableCounters } = filter;
        const { type: fieldType } = this.searchViewFields[fieldName];

        if (!enableCounters || !groups) {
            return {
                many2one: [],
                many2many: {},
            }[fieldType];
        }
        let groupDomain = null;
        if (fieldType === "many2one") {
            for (const group of groups.values()) {
                const valueIds = [];
                let active = false;
                for (const [valueId, value] of group.values) {
                    const { checked } = value;
                    valueIds.push(valueId);
                    if (checked) {
                        active = true;
                    }
                }
                if (active) {
                    if (groupDomain) {
                        groupDomain = [[0, "=", 1]];
                        break;
                    } else {
                        groupDomain = [[fieldName, "in", valueIds]];
                    }
                }
            }
        } else if (fieldType === "many2many") {
            const checkedValueIds = new Map();
            groups.forEach(({ values }, groupId) => {
                values.forEach(({ checked }, valueId) => {
                    if (checked) {
                        if (!checkedValueIds.has(groupId)) {
                            checkedValueIds.set(groupId, []);
                        }
                        checkedValueIds.get(groupId).push(valueId);
                    }
                });
            });
            groupDomain = {};
            for (const [gId, ids] of checkedValueIds.entries()) {
                for (const groupId of groups.keys()) {
                    if (gId !== groupId) {
                        const key = JSON.stringify(groupId);
                        if (!groupDomain[key]) {
                            groupDomain[key] = [];
                        }
                        groupDomain[key].push([fieldName, "in", ids]);
                    }
                }
            }
        }
        return groupDomain;
    }

    /**
     * Reconstruct the (active) groups from the query elements.
     * @returns {Object[]}
     */
    _getGroups() {
        const preGroups = [];
        for (const queryElem of this.query) {
            const { searchItemId } = queryElem;
            const { groupId } = this.searchItems[searchItemId];
            let preGroup = preGroups.find((group) => group.id === groupId);
            if (!preGroup) {
                preGroup = { id: groupId, queryElements: [] };
                preGroups.push(preGroup);
            }
            preGroup.queryElements.push(queryElem);
        }
        const groups = [];
        for (const preGroup of preGroups) {
            const { queryElements, id } = preGroup;
            let activeItems = [];
            for (const queryElem of queryElements) {
                const { searchItemId } = queryElem;
                let activeItem = activeItems.find(({ searchItemId: id }) => id === searchItemId);
                if ("generatorId" in queryElem) {
                    if (!activeItem) {
                        activeItem = { searchItemId, generatorIds: [] };
                        activeItems.push(activeItem);
                    }
                    activeItem.generatorIds.push(queryElem.generatorId);
                } else if ("intervalId" in queryElem) {
                    if (!activeItem) {
                        activeItem = { searchItemId, intervalIds: [] };
                        activeItems.push(activeItem);
                    }
                    activeItem.intervalIds.push(queryElem.intervalId);
                } else if ("autocompleteValue" in queryElem) {
                    if (!activeItem) {
                        activeItem = { searchItemId, autocompletValues: [] };
                        activeItems.push(activeItem);
                    }
                    activeItem.autocompletValues.push(queryElem.autocompleteValue);
                } else {
                    if (!activeItem) {
                        activeItem = { searchItemId };
                        activeItems.push(activeItem);
                    }
                }
            }
            for (const activeItem of activeItems) {
                if ("intervalIds" in activeItem) {
                    activeItem.intervalIds.sort((g1, g2) => rankInterval(g1) - rankInterval(g2));
                }
            }
            groups.push({ id, activeItems });
        }
        return groups;
    }

    /**
     *
     * @private
     * @param {Object} [params={}]
     * @returns {{ preFavorite: Object, irFilter: Object }}
     */
    _getIrFilterDescription(params = {}) {
        const { description, isDefault, isShared } = params;
        const fns = this.env.__getContext__.callbacks;
        const localContext = Object.assign({}, ...fns.map((fn) => fn()));
        const gs = this.env.__getOrderBy__.callbacks;
        let localOrderBy;
        if (gs.length) {
            localOrderBy = gs.flatMap((g) => g());
        }
        const context = makeContext([this._getContext(), localContext]);
        const userContext = this.userService.context;
        for (const key in context) {
            if (key in userContext || /^search(panel)?_default_/.test(key)) {
                // clean search defaults and user context keys
                delete context[key];
            }
        }
        const domain = this._getDomain({ raw: true, withGlobal: false }).toString();
        const groupBys = this._getGroupBy();
        const comparison = this.getFullComparison();
        const orderBy = localOrderBy || this._getOrderBy();
        const userId = isShared ? false : this.userService.userId;

        const preFavorite = {
            description,
            isDefault,
            domain,
            context,
            groupBys,
            orderBy,
            userId,
        };
        const irFilter = {
            name: description,
            action_id: this.env.config.actionId,
            model_id: this.resModel,
            domain,
            is_default: isDefault,
            sort: JSON.stringify(orderBy.map((o) => `${o.name}${o.asc === false ? " desc" : ""}`)),
            user_id: userId,
            context: { group_by: groupBys, ...context },
        };

        if (comparison) {
            preFavorite.comparison = comparison;
            irFilter.context.comparison = comparison;
        }

        return { preFavorite, irFilter };
    }

    /**
     * @returns {string[]}
     */
    _getOrderBy() {
        const groups = this._getGroups();
        let orderBy = [];
        for (const group of groups) {
            for (const activeItem of group.activeItems) {
                const { searchItemId } = activeItem;
                const searchItem = this.searchItems[searchItemId];
                if (searchItem.type === "favorite") {
                    orderBy.push(...searchItem.orderBy);
                }
            }
        }
        orderBy = orderBy.length ? orderBy : this.globalOrderBy;
        return typeof orderBy === "string" ? [orderBy] : orderBy;
    }

    /**
     * Return the context of the provided (active) filter.
     */
    _getSearchItemContext(activeItem) {
        const { searchItemId } = activeItem;
        const searchItem = this.searchItems[searchItemId];
        switch (searchItem.type) {
            case "field": {
                // for <field> nodes, a dynamic context (like context="{'field1': self}")
                // should set {'field1': [value1, value2]} in the context
                let context = {};
                if (searchItem.context) {
                    try {
                        const self = activeItem.autocompletValues.map(
                            (autocompleValue) => autocompleValue.value
                        );
                        context = evaluateExpr(searchItem.context, { self });
                        if (typeof context !== "object") {
                            throw Error();
                        }
                    } catch (error) {
                        throw new Error(
                            `${this.env._t("Failed to evaluate the context")} "${
                                searchItem.context
                            }".\n${error.message}`
                        );
                    }
                }
                // the following code aims to remodel this:
                // https://github.com/odoo/odoo/blob/12.0/addons/web/static/src/js/views/search/search_inputs.js#L498
                // this is required for the helpdesk tour to pass
                // this seems weird to only do that for m2o fields, but a test fails if
                // we do it for other fields (my guess being that the test should simply
                // be adapted)
                if (searchItem.isDefault && searchItem.fieldType === "many2one") {
                    context[`default_${searchItem.fieldName}`] =
                        searchItem.defaultAutocompleteValue.value;
                }
                return context;
            }
            case "favorite":
            case "filter": {
                //Return a deep copy of the filter/favorite to avoid the view to modify the context
                return makeContext([searchItem.context && deepCopy(searchItem.context)]);
            }
            default: {
                return null;
            }
        }
    }

    /**
     * Return the domain of the provided filter.
     */
    _getSearchItemDomain(activeItem) {
        const { searchItemId } = activeItem;
        const searchItem = this.searchItems[searchItemId];
        switch (searchItem.type) {
            case "field": {
                return this._getFieldDomain(searchItem, activeItem.autocompletValues);
            }
            case "dateFilter": {
                const { dateFilterId } = this._getActiveComparison() || {};
                if (this.searchMenuTypes.has("comparison") && dateFilterId === searchItemId) {
                    return new Domain([]);
                }
                return this._getDateFilterDomain(searchItem, activeItem.generatorIds);
            }
            case "filter":
            case "favorite": {
                return searchItem.domain;
            }
            default: {
                return null;
            }
        }
    }

    _getSearchItemGroupBys(activeItem) {
        const { searchItemId } = activeItem;
        const searchItem = this.searchItems[searchItemId];
        switch (searchItem.type) {
            case "dateGroupBy": {
                const { fieldName } = searchItem;
                return activeItem.intervalIds.map((intervalId) => `${fieldName}:${intervalId}`);
            }
            case "groupBy": {
                return [searchItem.fieldName];
            }
            case "favorite": {
                return searchItem.groupBys;
            }
            default: {
                return null;
            }
        }
    }

    /**
     * Starting from a date filter id, returns the array of option ids currently selected
     * for the corresponding date filter.
     */
    _getSelectedGeneratorIds(dateFilterId) {
        const selectedOptionIds = [];
        for (const queryElem of this.query) {
            if (queryElem.searchItemId === dateFilterId && "generatorId" in queryElem) {
                selectedOptionIds.push(queryElem.generatorId);
            }
        }
        return selectedOptionIds;
    }

    /**
     * @returns {Domain}
     */
    _getSearchPanelDomain() {
        return Domain.and([this._getCategoryDomain(), this._getFilterDomain()]);
    }

    /**
     * @param {Object} state
     */
    _importState(state) {
        execute(arraytoMap, state, this);
    }

    /**
     * @param {Object} irFilter
     */
    _irFilterToFavorite(irFilter) {
        let userId = false;
        if (Array.isArray(irFilter.user_id)) {
            userId = irFilter.user_id[0];
        }
        const groupNumber = userId ? FAVORITE_PRIVATE_GROUP : FAVORITE_SHARED_GROUP;
        const context = evaluateExpr(irFilter.context, this.userService.context);
        let groupBys = [];
        if (context.group_by) {
            groupBys = context.group_by;
            delete context.group_by;
        }
        let comparison;
        if (context.comparison) {
            comparison = context.comparison;
            if (typeof comparison.range === "string") {
                // legacy case
                comparison.range = new Domain(comparison.range).toList();
            }
            if (typeof comparison.comparisonRange === "string") {
                // legacy case
                comparison.comparisonRange = new Domain(comparison.comparisonRange).toList();
            }
            delete context.comparison;
        }
        let sort;
        try {
            sort = JSON.parse(irFilter.sort);
        } catch (err) {
            if (err instanceof SyntaxError) {
                sort = [];
            } else {
                throw err;
            }
        }
        const orderBy = sort.map((order) => {
            let fieldName;
            let asc;
            const sqlNotation = order.split(" ");
            if (sqlNotation.length > 1) {
                // regex: \fieldName (asc|desc)?\
                fieldName = sqlNotation[0];
                asc = sqlNotation[1] === "asc";
            } else {
                // legacy notation -- regex: \-?fieldName\
                fieldName = order[0] === "-" ? order.slice(1) : order;
                asc = order[0] === "-" ? false : true;
            }
            return {
                asc: asc,
                name: fieldName,
            };
        });
        const favorite = {
            context,
            description: irFilter.name,
            domain: irFilter.domain,
            groupBys,
            groupNumber,
            orderBy,
            removable: true,
            serverSideId: irFilter.id,
            type: "favorite",
            userId,
        };
        if (irFilter.is_default) {
            favorite.isDefault = irFilter.is_default;
        }
        if (comparison) {
            favorite.comparison = comparison;
        }
        return favorite;
    }

    async _notify() {
        if (this.blockNotification) {
            return;
        }

        this._reset();

        await this._reloadSections();

        this.trigger("update");
    }

    /**
     * Updates the search domain and reloads sections if:
     * - the current search domain is different from the previous, or...
     * - a `shouldReload` flag has been set to true on the searchPanelInfo.
     * The latter means that the search domain has been modified while the
     * search panel was not displayed (and thus not reloaded) and the reload
     * should occur as soon as the search panel is visible again.
     * @private
     * @returns {Promise<void>}
     */
    async _reloadSections() {
        this.blockNotification = true;

        // Check whether the search domain changed
        const searchDomain = this._getDomain({ withSearchPanel: false });
        const searchDomainChanged =
            this.searchPanelInfo.shouldReload ||
            JSON.stringify(this.searchDomain) !== JSON.stringify(searchDomain);
        this.searchDomain = searchDomain;

        // Check whether categories/filters will force a reload of the sections
        const toFetch = (section) =>
            section.enableCounters || (searchDomainChanged && !section.expand);
        const categoriesToFetch = this.categories.filter(toFetch);
        const filtersToFetch = this.filters.filter(toFetch);

        if (searchDomainChanged || Boolean(categoriesToFetch.length + filtersToFetch.length)) {
            if (this.display.searchPanel) {
                this.sectionsPromise = this._fetchSections(categoriesToFetch, filtersToFetch);
                if (this._shouldWaitForData(searchDomainChanged)) {
                    await this.sectionsPromise;
                }
            }
            // If no current search panel: will try to reload on next model update
            this.searchPanelInfo.shouldReload = !this.display.searchPanel;
        }

        this.blockNotification = false;
    }

    _reset() {
        delete this._comparison;
        this._context = null;
        this._domain = null;
        this._groupBy = null;
        this._orderBy = null;
    }

    /**
     * Returns whether the query informations should be considered as ready
     * before or after having (re-)fetched the sections data.
     * @param {boolean} searchDomainChanged
     * @returns {boolean}
     */
    _shouldWaitForData(searchDomainChanged) {
        if (this.categories.length && this.filters.some((filter) => filter.domain !== "[]")) {
            // Selected category value might affect the filter values
            return true;
        }
        if (!this.searchDomain.length) {
            // No search domain -> no need to check for expand
            return false;
        }
        return [...this.sections.values()].some(
            (section) => !section.expand && searchDomainChanged
        );
    }

    /**
     * Legacy compatibility: the imported state of a legacy search panel model
     * extension doesn't include the arch information, i.e. the class name and
     * view types. We have to extract those if they are not given.
     * @param {Object} searchViewDescription
     * @param {Object} searchViewFields
     */
    __legacyParseSearchPanelArchAnyway(searchViewDescription, searchViewFields) {
        if (this.searchPanelInfo) {
            return;
        }

        const parser = new SearchArchParser(searchViewDescription, searchViewFields);
        const { searchPanelInfo } = parser.parse();

        this.searchPanelInfo = { ...searchPanelInfo, loaded: false, shouldReload: false };
    }
}
