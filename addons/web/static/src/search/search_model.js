import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { user } from "@web/core/user";
import { groupBy, sortBy } from "@web/core/utils/arrays";
import { deepCopy } from "@web/core/utils/objects";
import { SearchArchParser } from "./search_arch_parser";
import {
    constructDateDomain,
    DEFAULT_INTERVAL,
    getIntervalOptions,
    getPeriodOptions,
    INTERVAL_OPTIONS,
    rankInterval,
    yearSelected,
} from "./utils/dates";
import { FACET_COLORS, FACET_ICONS } from "./utils/misc";

import { EventBus, toRaw } from "@odoo/owl";
import { getDefaultDomain } from "@web/core/domain_selector/utils";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { _t } from "@web/core/l10n/translation";
import { domainFromTree, treeFromDomain } from "@web/core/tree_editor/condition_tree";
import { useGetTreeDescription, useMakeGetFieldDef } from "@web/core/tree_editor/utils";
import { rpcBus } from "@web/core/network/rpc";

const { DateTime } = luxon;
const SPECIAL = Symbol("special");

/**
 * @typedef {import("@web/core/domain").DomainListRepr} DomainListRepr
 * @typedef {import("@web/search/utils/order_by").OrderTerm} OrderTerm
 */

/**
 * @typedef {Object} SearchParams
 * @property {Context} context
 * @property {DomainListRepr} domain
 * @property {string[]} groupBy
 * @property {OrderTerm[]} orderBy
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
    const { query, nextId, nextGroupId, nextGroupNumber, searchItems, searchPanelInfo, sections } =
        source;

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
    constructor(env, services, args) {
        super();
        this.env = env;
        this.setup(services, args);
    }
    /**
     * @override
     */
    setup(services) {
        // services
        const { field: fieldService, name: nameService, orm, view, dialog } = services;
        this.orm = orm;
        this.fieldService = fieldService;
        this.viewService = view;
        this.dialog = dialog;
        this.orderByCount = false;

        this.getDomainTreeDescription = useGetTreeDescription(fieldService, nameService);
        this.makeGetFieldDef = useMakeGetFieldDef(fieldService);

        // used to manage search items related to date/datetime fields
        this.referenceMoment = DateTime.local();
        this.intervalOptions = getIntervalOptions();
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
     * @param {Object} [config.context={}]
     * @param {Array} [config.domain=[]]
     * @param {Array} [config.dynamicFilters=[]]
     * @param {string[]} [config.groupBy=[]]
     * @param {boolean} [config.loadIrFilters=false]
     * @param {boolean} [config.display.searchPanel=true]
     * @param {OrderTerm[]} [config.orderBy=[]]
     * @param {string[]} [config.searchMenuTypes=["filter", "groupBy", "favorite"]]
     * @param {Object} [config.state]
     */
    async load(config) {
        const { resModel } = config;
        if (!resModel) {
            throw Error(`SearchModel config should have a "resModel" key`);
        }
        this.resModel = resModel;

        // used to avoid useless recomputations
        this._reset();

        const { context, domain, groupBy, hideCustomGroupBy, orderBy } = config;

        this.globalContext = toRaw(Object.assign({}, context));
        this.globalDomain = domain || [];
        this.globalGroupBy = groupBy || [];
        this.globalOrderBy = orderBy || [];
        this.hideCustomGroupBy = hideCustomGroupBy;

        this.searchMenuTypes = new Set(config.searchMenuTypes || ["filter", "groupBy", "favorite"]);
        this.canOrderByCount = config.canOrderByCount;
        this.defaultGroupBy = config.defaultGroupBy;

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
                    embeddedActionId: this.env.config.currentEmbeddedActionId,
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

        const { searchDefaults, searchPanelDefaults } =
            this._extractSearchDefaultsFromGlobalContext();

        if (config.state) {
            this._importState(config.state);
            this.__legacyParseSearchPanelArchAnyway(searchViewDescription, searchViewFields);
            this.display = this._getDisplay(config.display);
            this._reconciliateFavorites();
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
     * @param {Object} [config.context={}]
     * @param {Array} [config.domain=[]]
     * @param {string[]} [config.groupBy=[]]
     * @param {OrderTerm[]} [config.orderBy=[]]
     */
    async reload(config = {}) {
        this._reset();

        const { context, domain, groupBy, orderBy } = config;

        this.globalContext = Object.assign({}, context);
        this.globalDomain = domain || [];
        this.globalGroupBy = groupBy || [];
        this.globalOrderBy = orderBy || [];

        this._extractSearchDefaultsFromGlobalContext();

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
            this._context = makeContext([this.globalContext, this._getContext()]);
        }
        return deepCopy(this._context);
    }

    /**
     * @returns {DomainListRepr}
     */
    get domain() {
        if (!this._domain) {
            this._domain = this._getDomain();
        }
        return deepCopy(this._domain);
    }

    /**
     * @returns {string}
     */
    get domainString() {
        return this._getDomain({ raw: true }).toString();
    }

    get domainEvalContext() {
        return Object.assign({}, this.globalContext, user.context);
    }

    get facets() {
        const facets = [];
        for (const facet of this._getFacets()) {
            if (facet.type === "groupBy" && !this.searchMenuTypes.has(facet.type)) {
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
        if (!this.searchMenuTypes.has("groupBy")) {
            return [];
        }
        if (!this._groupBy) {
            this._groupBy = this._getGroupBy();
        }
        return deepCopy(this._groupBy);
    }

    /**
     * @returns {OrderTerm[]}
     */
    get orderBy() {
        if (!this._orderBy) {
            this._orderBy = this._getOrderBy();
        }
        return deepCopy(this._orderBy);
    }

    get isDebugMode() {
        return !!this.env.debug;
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
        if (!["field", "field_property"].includes(searchItem.type)) {
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
        this.orderByCount = false;
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
        const serverSideId = await this._createIrFilters(irFilter);

        // before the filter cache was cleared!
        this.blockNotification = true;
        this.clearQuery();
        const favorite = {
            ...preFavorite,
            type: "favorite",
            id: this.nextId,
            groupId: this.nextGroupId,
            groupNumber:
                preFavorite.userIds.length === 1 ? FAVORITE_PRIVATE_GROUP : FAVORITE_SHARED_GROUP,
            removable: true,
            serverSideId,
        };
        this.searchItems[this.nextId] = favorite;
        this.query.push({ searchItemId: this.nextId });
        this.nextGroupId++;
        this.nextId++;
        this.blockNotification = false;
        this._notify();
        return serverSideId;
    }

    async _createIrFilters(irFilter) {
        const serverSideIds = await this.orm.call("ir.filters", "create_filter", [irFilter]);
        rpcBus.trigger("CLEAR-CACHES", "get_views");
        return serverSideIds[0];
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
     * @param {Object} [param]
     * @param {string} [param.interval=DEFAULT_INTERVAL]
     * @param {boolean} [param.invisible=false]
     */
    createNewGroupBy(fieldName, { interval, invisible } = {}) {
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
        if (invisible) {
            preSearchItem.invisible = "True";
        }
        if (["date", "datetime"].includes(fieldType)) {
            this.searchItems[this.nextId] = Object.assign(
                { type: "dateGroupBy", defaultIntervalId: interval || DEFAULT_INTERVAL },
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
        if (groupId === SPECIAL) {
            delete this.defaultGroupBy;
            this._notify();
            return;
        }
        this.query = this.query.filter((queryElem) => {
            const searchItem = this.searchItems[queryElem.searchItemId];
            return searchItem.groupId !== groupId;
        });
        this._checkOrderByCountStatus();
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

    getIrFilterValues(params) {
        const { irFilter } = this._getIrFilterDescription(params);
        return irFilter;
    }

    getPreFavoriteValues(params) {
        const { preFavorite } = this._getIrFilterDescription(params);
        return preFavorite;
    }

    /**
     * Return an array containing enriched copies of all searchElements or of those
     * satifying the given predicate if any
     * @param {Function} [predicate]
     * @returns {Object[]}
     */
    getSearchItems(predicate) {
        const searchItems = [];
        for (const searchItem of Object.values(this.searchItems)) {
            const enrichedSearchitem = this._enrichItem(searchItem);
            if (enrichedSearchitem) {
                const isInvisible =
                    "invisible" in searchItem &&
                    evaluateExpr(searchItem.invisible, this.domainEvalContext);
                if (!isInvisible && (!predicate || predicate(enrichedSearchitem))) {
                    searchItems.push(enrichedSearchitem);
                }
            }
        }
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

    async splitAndAddDomain(domain, groupId) {
        const group = groupId ? this._getGroups().find((g) => g.id === groupId) : null;
        let context;
        if (group) {
            const contexts = [];
            for (const activeItem of group.activeItems) {
                const context = this._getSearchItemContext(activeItem);
                if (context) {
                    contexts.push(context);
                }
            }
            context = makeContext(contexts);
        }

        const getFieldDef = await this.makeGetFieldDef(this.resModel, treeFromDomain(domain));
        const tree = treeFromDomain(domain, { distributeNot: !this.isDebugMode, getFieldDef });
        const trees = !tree.negate && tree.value === "&" ? tree.children : [tree];
        const promises = trees.map(async (tree) => {
            const description = await this.getDomainTreeDescription(this.resModel, tree);
            const preFilter = {
                description,
                domain: domainFromTree(tree),
                invisible: "True",
                type: "filter",
            };
            if (context) {
                preFilter.context = context;
            }
            return preFilter;
        });

        const preFilters = await Promise.all(promises);

        this.blockNotification = true;

        if (group) {
            const firstActiveItem = group.activeItems[0];
            const firstSearchItem = this.searchItems[firstActiveItem.searchItemId];
            const { type } = firstSearchItem;
            if (type === "favorite") {
                const activeItemGroupBys = this._getSearchItemGroupBys(firstActiveItem);
                for (const activeItemGroupBy of activeItemGroupBys) {
                    const [fieldName, interval] = activeItemGroupBy.split(":");
                    this.createNewGroupBy(fieldName, { interval, invisible: true });
                }
                const index = this.query.length - activeItemGroupBys.length;
                this.query = [...this.query.slice(index), ...this.query.slice(0, index)];
            }
            this.deactivateGroup(groupId);
        }

        for (const preFilter of preFilters) {
            this.createNewFilters([preFilter]);
        }

        this.blockNotification = false;

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
     * Clears all values from the provided sections
     * @param {array} sectionIds
     */
    clearSections(sectionIds) {
        for (const sectionId of sectionIds) {
            const section = this.sections.get(sectionId);
            if (section.type === "category") {
                section.activeValueId = false;
            } else {
                for (const [, value] of section.values) {
                    value.checked = false;
                }
            }
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
            case "field_property":
            case "field": {
                return;
            }
        }
        const index = this.query.findIndex((queryElem) => queryElem.searchItemId === searchItemId);
        if (index >= 0) {
            this.query.splice(index, 1);
            this._checkOrderByCountStatus();
        } else {
            if (searchItem.type === "favorite") {
                this.query = [];
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
        const generatorIds = generatorId ? [generatorId] : searchItem.defaultGeneratorIds;
        for (const generatorId of generatorIds) {
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
                if (generatorId.startsWith("custom")) {
                    this.query = this.query.filter(
                        (queryElem) => searchItemId !== queryElem.searchItemId
                    );
                    this.query.push({ searchItemId, generatorId });
                    continue;
                }
                this.query = this.query.filter(
                    (queryElem) =>
                        queryElem.searchItemId !== searchItemId ||
                        !queryElem.generatorId.startsWith("custom")
                );
                this.query.push({ searchItemId, generatorId });
                if (!yearSelected(this._getSelectedGeneratorIds(searchItemId))) {
                    // Here we add 'year' as options if no option of type
                    // year is already selected.
                    const { defaultYearId } = getPeriodOptions(
                        this.referenceMoment,
                        searchItem.optionsParams
                    ).find((o) => o.id === generatorId);
                    this.query.push({ searchItemId, generatorId: defaultYearId });
                }
            }
        }
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
            this._checkOrderByCountStatus();
        } else {
            this.query.push({ searchItemId, intervalId });
        }
        this._notify();
    }

    async spawnCustomFilterDialog() {
        const domain = getDefaultDomain(this.searchViewFields);
        this.dialog.add(DomainSelectorDialog, {
            resModel: this.resModel,
            defaultConnector: "|",
            domain,
            context: this.globalContext,
            onConfirm: (domain) => this.splitAndAddDomain(domain),
            disableConfirmButton: (domain) => domain === `[]`,
            title: _t("Add Custom Filter"),
            confirmButtonText: _t("Add"),
            discardButtonText: _t("Cancel"),
            isDebugMode: this.isDebugMode,
        });
    }

    switchGroupBySort() {
        if (this.orderByCount === "Desc") {
            this.orderByCount = "Asc";
        } else {
            this.orderByCount = "Desc";
        }
        this._notify();
    }

    /**
     * Generate the searchItems corresponding to the properties.
     * @param {Object} searchItem
     * @returns {Object[]}
     */
    async getSearchItemsProperties(searchItem) {
        if (searchItem.type !== "field" || searchItem.fieldType !== "properties") {
            return [];
        }
        const field = this.searchViewFields[searchItem.fieldName];
        const definitionRecord = field.definition_record;
        const result = await this._fetchPropertiesDefinition(this.resModel, searchItem.fieldName);

        const searchItemIds = new Set();
        const existingFieldProperties = {};
        for (const item of Object.values(this.searchItems)) {
            if (item.type === "field_property" && item.propertyItemId === searchItem.id) {
                existingFieldProperties[item.propertyFieldDefinition.name] = item;
            }
        }

        for (const { definitionRecordId, definitionRecordName, definitions } of result) {
            for (const definition of definitions) {
                if (definition.type === "separator") {
                    continue;
                }
                const existingSearchItem = existingFieldProperties[definition.name];
                if (existingSearchItem) {
                    // already in the list, can happen if we unfold the properties field
                    // open a form view, edit the property and then go back to the search view
                    // the label of the property might have been changed
                    existingSearchItem.description = `${definition.string} (${definitionRecordName})`;
                    searchItemIds.add(existingSearchItem.id);
                    continue;
                }
                const id = this.nextId++;
                const newSearchItem = {
                    id,
                    type: "field_property",
                    fieldName: searchItem.fieldName,
                    propertyDomain: [definitionRecord, "=", definitionRecordId],
                    propertyFieldDefinition: definition,
                    propertyItemId: searchItem.id,
                    description: `${definition.string} (${definitionRecordName})`,
                    groupId: this.nextGroupId++,
                };
                if (["many2many", "tags"].includes(definition.type)) {
                    newSearchItem.operator = "in";
                }
                this.searchItems[id] = newSearchItem;
                searchItemIds.add(id);
            }
        }

        return this.getSearchItems((searchItem) => searchItemIds.has(searchItem.id));
    }

    //--------------------------------------------------------------------------
    // Private methods
    //--------------------------------------------------------------------------

    /**
     * Because it require a RPC to get the properties search views items,
     * it's done lazily, only when we need them.
     */
    async fillSearchViewItemsProperty() {
        if (!this.searchViewFields) {
            return;
        }

        const fields = Object.values(this.searchViewFields);

        for (const field of fields) {
            if (field.type !== "properties") {
                continue;
            }

            const result = await this._fetchPropertiesDefinition(this.resModel, field.name);

            const searchItemsNames = Object.values(this.searchItems)
                .filter((item) => item.isProperty && ["groupBy", "dateGroupBy"].includes(item.type))
                .map((item) => item.fieldName);

            for (const { definitionRecordId, definitionRecordName, definitions } of result) {
                // some properties might have been deleted
                const groupNames = definitions.map(
                    (definition) => `group_by_${field.name}.${definition.name}`
                );
                Object.values(this.searchItems).forEach((searchItem) => {
                    if (
                        searchItem.isProperty &&
                        searchItem.definitionRecordId === definitionRecordId &&
                        ["groupBy", "dateGroupBy"].includes(searchItem.type) &&
                        !groupNames.includes(searchItem.name)
                    ) {
                        // we can not just remove the element from the list because index are used as id
                        // so we use a different type to hide it everywhere (until the user refresh his
                        // browser and the item won't be created again)
                        searchItem.type = "group_by_property_deleted";
                    }
                });

                for (const definition of definitions) {
                    // we need the definition of the "field" (fake field, property) to be
                    // in searchViewFields to be able to have the type, it's description, etc
                    // the name of the property is stored as "<properties field name>.<property name>"
                    const fullName = `${field.name}.${definition.name}`;
                    this.searchViewFields[fullName] = {
                        name: fullName,
                        readonly: false,
                        relation: definition.comodel,
                        required: false,
                        searchable: false,
                        selection: definition.selection,
                        sortable: true,
                        store: true,
                        string: definition.string,
                        type: definition.type,
                        relatedPropertyField: field,
                    };

                    if (!searchItemsNames.includes(fullName) && definition.type !== "separator") {
                        const groupByItem = {
                            description: definition.string,
                            definitionRecordId,
                            definitionRecordName,
                            fieldName: fullName,
                            fieldType: definition.type,
                            isProperty: true,
                            name: `group_by_${field.name}.${definition.name}`,
                            propertyFieldName: field.name,
                            type: ["datetime", "date"].includes(definition.type)
                                ? "dateGroupBy"
                                : "groupBy",
                        };
                        this._createGroupOfSearchItems([groupByItem]);
                    }
                }
            }
        }
    }

    /**
     * Fetch the properties definitions.
     *
     * @param {string} definitionRecordModel
     * @param {string} definitionRecordField
     * @return {Object[]} A list of objects of the form
     *      {
     *          definitionRecordId: <id of the parent record>
     *          definitionRecordName: <display name of the parent record>
     *          definitions: <list of properties definitions>
     *      }
     */
    async _fetchPropertiesDefinition(resModel, fieldName) {
        const domain = [];
        if (this.context.active_id) {
            // assume the active id is the definition record
            // and show only its properties
            domain.push(["id", "=", this.context.active_id]);
        }

        const definitions = await this.fieldService.loadPropertyDefinitions(
            resModel,
            fieldName,
            domain
        );
        const result = groupBy(Object.values(definitions), (definition) => definition.record_id);
        return Object.entries(result).map(([recordId, definitions]) => ({
            definitionRecordId: parseInt(recordId),
            definitionRecordName: definitions[0]?.record_name,
            definitions,
        }));
    }

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

    _checkOrderByCountStatus() {
        if (
            this.orderByCount &&
            !this.query.some((item) =>
                ["dateGroupBy", "groupBy"].includes(this.searchItems[item.searchItemId].type)
            )
        ) {
            this.orderByCount = false;
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
                        color_index: value.color_index,
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
     * Add filters of type 'filter' determined by the key array dynamicFilters.
     */
    _createGroupOfDynamicFilters(dynamicFilters) {
        const pregroup = dynamicFilters.map((filter) => ({
            groupNumber: this.nextGroupNumber,
            description: filter.description,
            domain: filter.domain,
            isDefault: "is_default" in filter ? filter.is_default : true,
            type: "filter",
        }));
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
        if (searchItem.type === "field" && searchItem.fieldType === "properties") {
            return { ...searchItem };
        }
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
            case "dateFilter":
                enrichSearchItem.options = _enrichOptions(
                    getPeriodOptions(this.referenceMoment, searchItem.optionsParams),
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
            case "field_property":
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

    _extractSearchDefaultsFromGlobalContext() {
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
        return { searchDefaults, searchPanelDefaults };
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
                        context: this.globalContext,
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
                        context: this.globalContext,
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
        const contexts = [user.context];
        for (const group of groups) {
            for (const activeItem of group.activeItems) {
                const context = this._getSearchItemContext(activeItem);
                if (context) {
                    contexts.push(context);
                }
            }
        }
        return makeContext(contexts);
    }

    /**
     * Compute the string representation or the description of the current domain associated
     * with a date filter starting from its corresponding query elements.
     */
    _getDateFilterDomain(dateFilter, generatorIds, key = "domain") {
        const dateFilterRange = constructDateDomain(this.referenceMoment, dateFilter, generatorIds);
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
     * @returns {{ controlPanel: Object | false, searchPanel: boolean, banner: boolean }}
     */
    _getDisplay(display = {}) {
        const { viewTypes } = this.searchPanelInfo;
        const { viewType } = this.env.config;
        return {
            controlPanel: "controlPanel" in display ? display.controlPanel : {},
            searchPanel:
                this.sections.size &&
                (!viewType || viewTypes.includes(viewType)) &&
                ("searchPanel" in display ? display.searchPanel : true),
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

        // we need to manage (optional) facets, deactivateGroup, clearQuery,...

        if (this.display.searchPanel && withSearchPanel) {
            domains.push(this._getSearchPanelDomain());
        }

        const domain = Domain.and(domains);
        return params.raw ? domain : domain.toList(this.domainEvalContext);
    }

    _getFacets() {
        const facets = [];
        const groups = this._getGroups();
        for (const group of groups) {
            const groupActiveItemDomains = [];
            const values = [];
            let title;
            let type;
            for (const activeItem of group.activeItems) {
                const domain = this._getSearchItemDomain(activeItem);
                if (domain) {
                    groupActiveItemDomains.push(domain);
                }
                const searchItem = this.searchItems[activeItem.searchItemId];
                switch (searchItem.type) {
                    case "field_property":
                    case "field": {
                        type = "field";
                        title = searchItem.description;
                        for (const autocompleteValue of activeItem.autocompletValues) {
                            values.push(autocompleteValue.labelForFacet || autocompleteValue.label);
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
                            const { description } = INTERVAL_OPTIONS[intervalId];
                            values.push(`${searchItem.description}: ${description}`);
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
                type,
                values,
                separator: type === "groupBy" ? ">" : _t("or"),
            };
            if (type === "field") {
                facet.title = title;
            } else {
                if (type === "groupBy" && this.orderByCount) {
                    facet.icon =
                        FACET_ICONS[this.orderByCount === "Asc" ? "groupByAsc" : "groupByDesc"];
                } else {
                    facet.icon = FACET_ICONS[type];
                }
                facet.color = FACET_COLORS[type];
            }
            if (groupActiveItemDomains.length) {
                facet.domain = Domain.or(groupActiveItemDomains).toString();
            }
            facets.push(facet);
        }
        const hasAGroupByFacet = facets.some((f) => f.type === "groupBy");
        if (
            !hasAGroupByFacet &&
            !this.globalGroupBy.length &&
            this.defaultGroupBy &&
            this.env.config.viewType !== "kanban"
        ) {
            facets.unshift({
                groupId: SPECIAL,
                type: "groupBy",
                values: this.defaultGroupBy.map((gb) => {
                    const [fieldName, interval] = gb.split(":");
                    const { string } = this.searchViewFields[fieldName];
                    if (interval) {
                        const { description } = INTERVAL_OPTIONS[interval];
                        return `${string}:${description}`;
                    }
                    return string;
                }),
                separator: ">",
                icon: FACET_ICONS.groupBy,
                color: FACET_COLORS.groupBy,
            });
        }
        return facets;
    }

    /**
     * Return the domain resulting from the combination of the autocomplete values
     * of a search item of type 'field'.
     */
    _getFieldDomain(field, autocompleteValues) {
        const domains = autocompleteValues.map(({ label, value, operator, enforceOperator }) => {
            let domain;
            if (field.filterDomain) {
                let filterDomain = field.filterDomain;
                if (enforceOperator) {
                    filterDomain = field.filterDomain
                        .replaceAll("'ilike'", `'${operator}'`)
                        .replaceAll('"ilike"', `"${operator}"`);
                }
                domain = new Domain(filterDomain).toList({
                    self: label.trim(),
                    raw_value: value,
                });
            } else if (field.type === "field") {
                domain = [[field.fieldName, operator, value]];
            } else if (field.type === "field_property") {
                domain = [
                    field.propertyDomain,
                    [`${field.fieldName}.${field.propertyFieldDefinition.name}`, operator, value],
                ];
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
        const groupBy = groupBys.length
            ? groupBys
            : this.globalGroupBy.length
            ? this.globalGroupBy.slice()
            : this.defaultGroupBy?.slice() || [];
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
            const activeItems = [];
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
        const { description, isDefault, isShared, embeddedActionId } = params;
        const fns = this.env.__getContext__.callbacks;
        const localContext = Object.assign({}, ...fns.map((fn) => fn()));
        const gs = this.env.__getOrderBy__.callbacks;
        let localOrderBy;
        if (gs.length) {
            localOrderBy = gs.flatMap((g) => g());
        }
        const context = makeContext([this._getContext(), localContext]);
        const userContext = user.context;
        for (const key in context) {
            if (key in userContext || /^search(panel)?_default_/.test(key)) {
                // clean search defaults and user context keys
                delete context[key];
            }
        }
        const domain = this._getDomain({ raw: true, withGlobal: false }).toString();
        const groupBys = this._getGroupBy();
        const orderBy = localOrderBy || this._getOrderBy();
        const userIds = isShared ? [] : [user.userId];

        const preFavorite = {
            description,
            isDefault,
            domain,
            context,
            groupBys,
            orderBy,
            userIds,
        };
        const irFilter = {
            name: description,
            action_id: this.env.config.actionId,
            model_id: this.resModel,
            domain,
            embedded_action_id: embeddedActionId,
            embedded_parent_res_id: this.globalContext.active_id || false,
            is_default: isDefault,
            sort: JSON.stringify(orderBy.map((o) => `${o.name}${o.asc === false ? " desc" : ""}`)),
            user_ids: userIds,
            context: { group_by: groupBys, ...context },
        };

        return { preFavorite, irFilter };
    }

    /**
     * @returns {OrderTerm[]}
     */
    _getOrderBy() {
        const groups = this._getGroups();
        const orderBy = [];
        if (this.groupBy.length && this.orderByCount) {
            orderBy.push({ name: "__count", asc: this.orderByCount === "Asc" });
        }
        for (const group of groups) {
            for (const activeItem of group.activeItems) {
                const { searchItemId } = activeItem;
                const searchItem = this.searchItems[searchItemId];
                if (searchItem.type === "favorite") {
                    orderBy.push(...searchItem.orderBy);
                }
            }
        }
        return orderBy.length ? orderBy : this.globalOrderBy;
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
                    const self = activeItem.autocompletValues.map(
                        (autocompleValue) => autocompleValue.value
                    );
                    context = evaluateExpr(searchItem.context, { self });
                    if (typeof context !== "object") {
                        throw new Error(
                            _t("Failed to evaluate the context: %(context)s.", {
                                context: searchItem.context,
                            })
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
            case "field_property":
            case "field": {
                return this._getFieldDomain(searchItem, activeItem.autocompletValues);
            }
            case "dateFilter": {
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
        const userIds = irFilter.user_ids;
        const groupNumber = userIds.length === 1 ? FAVORITE_PRIVATE_GROUP : FAVORITE_SHARED_GROUP;
        const context = evaluateExpr(irFilter.context, user.context);
        let groupBys = [];
        if (context.group_by) {
            groupBys = context.group_by;
            delete context.group_by;
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
            userIds,
        };
        if (irFilter.is_default) {
            favorite.isDefault = irFilter.is_default;
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
     * Reconciliate the search items with the ir.filters.
     * @private
     */
    _reconciliateFavorites() {
        const irFilters = this.irFilters || [];
        const mapping = Object.fromEntries(irFilters.map((i) => [i.id, i]));
        for (const item of Object.values(this.searchItems)) {
            if (item.type !== "favorite") {
                continue;
            }
            const irFilter = mapping[item.serverSideId];
            if (irFilter) {
                Object.assign(item, this._irFilterToFavorite(irFilter));
                delete mapping[item.serverSideId];
            } else {
                const queryIndex = this.query.findIndex((q) => q.searchItemId === item.id);
                if (queryIndex !== -1) {
                    this.query.splice(queryIndex, 1);
                }
                delete this.searchItems[item.id];
            }
        }
        this._createGroupOfFavorites(Object.values(mapping));
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
