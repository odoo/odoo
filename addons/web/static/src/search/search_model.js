// @ts-check

/** @module @web/search/search_model - Search state machine managing facets, domains, groupbys, favorites, and comparisons */

import { EventBus, toRaw } from "@odoo/owl";
import { getDefaultDomain } from "@web/components/domain_selector/utils";
import { DomainSelectorDialog } from "@web/components/domain_selector_dialog/domain_selector_dialog";
import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { rpcBus } from "@web/core/network/rpc";
import { evaluateExpr } from "@web/core/py_js/py";
import { deepCopy } from "@web/core/utils/collections/objects";
import { user } from "@web/services/user";

import { SearchArchParser } from "./search_arch_parser";
import { computeSearchContext, computeSearchItemContext } from "./search_context";
import {
    computeCategoryDomain,
    computeDateFilterDomain,
    computeDomain,
    computeFieldDomain,
    computeFilterDomain,
    computeGroupDomain,
    computeSearchItemDomain,
    computeSearchPanelDomain,
} from "./search_domain";
import { enrichSearchItem } from "./search_enrichment";
import { buildFacets } from "./search_facets";
import {
    buildIrFilterDescription,
    irFilterToFavorite,
    reconciliateFavorites,
} from "./search_favorites";
import {
    computeGroupBy,
    computeOrderBy,
    computeSearchItemGroupBys,
    getQueryGroups,
    getSelectedGeneratorIds,
} from "./search_group_by";
import { createCategoryTree, createFilterTree } from "./search_panel_fetch";
import {
    fetchPropertiesDefinition as _fetchPropertiesDefinition,
    fillSearchViewItemsProperty as _fillSearchViewItemsProperty,
    getSearchItemsProperties as _getSearchItemsProperties,
} from "./search_properties";
import { splitAndAddDomain as _splitAndAddDomain } from "./search_split_domain";
import {
    arrayToMap,
    execute,
    extractSearchDefaults,
    FAVORITE_PRIVATE_GROUP,
    FAVORITE_SHARED_GROUP,
    hasValues,
    mapToArray,
    SPECIAL,
} from "./search_state";
import {
    DEFAULT_INTERVAL,
    getIntervalOptions,
    getPeriodOptions,
    yearSelected,
} from "./utils/dates";

/** @import { Context } from "@web/core/context" */
/** @import { DomainListRepr } from "@web/core/domain" */
/** @import { OrderTerm } from "@web/core/utils/order_by" */

const { DateTime } = luxon;

/**
 * @typedef {Object} Section
 * @property {number} id
 * @property {string} type
 * @property {Map<any, Object>} values
 * @property {Map<any, Object>} [groups]
 * @property {string} [errorMsg]
 * @property {string} [fieldName]
 * @property {string} [description]
 * @property {boolean} [enableCounters]
 * @property {number} [limit]
 * @property {string} [icon]
 * @property {string} [color]
 * @property {boolean} [expand]
 * @property {string|false} [hierarchize]
 * @property {number} [index]
 * @property {any} [activeValueId]
 * @property {string} [domain]
 * @property {string|false} [groupBy]
 *
 * @typedef {Section & { type: "category" }} Category
 * @typedef {Section & { type: "filter" }} Filter
 * @typedef {(section: Section) => boolean} SectionPredicate
 */

/**
 * @typedef {{
 *  name: string;
 *  type: string;
 *  selection?: [string | number, string][];
 *  relation?: string;
 *  relation_field?: string;
 *  relatedPropertyField?: string;
 *  definition_record?: string;
 *  definition_record_field?: string;
 *  context?: Context | string;
 *  domain?: DomainListRepr | string;
 *  currency_field?: string;
 *  falsy_value_label?: string;
 *  string?: string;
 *  readonly?: boolean;
 *  required?: boolean;
 *  searchable?: boolean;
 *  sortable?: boolean;
 *  store?: boolean;
 *  groupable?: boolean;
 *  aggregator?: string;
 *  [key: string]: any;
 * }} Field
 *
 * @typedef {{
 *  context: Context | string;
 *  forceSave?: boolean;
 *  invisible: string;
 *  isHandle?: boolean;
 *  onChange: boolean;
 *  readonly: string;
 *  required: string;
 *  related?: { activeFields: Record<string, FieldInfo>; fields: Record<string, Field> };
 *  limit?: number;
 *  defaultOrderBy?: import("@web/core/utils/order_by").OrderTerm[];
 *  relatedPropertyField?: string;
 *  [key: string]: any;
 * }} FieldInfo
 *
 * @typedef {{
 *  context: Context;
 *  domain: DomainListRepr;
 *  groupBy: string[];
 *  orderBy: OrderTerm[];
 *  resModel: string;
 *  resId?: number | false;
 *  resIds?: number[];
 *  useSampleModel?: boolean;
 *  [key: string]: any;
 * }} SearchParams
 */

export class SearchModel extends EventBus {
    constructor(env, services, args) {
        super();
        this.env = env;
        this.setup(services, args);
    }

    setup(services, _args) {
        // services
        const { field: fieldService, orm, view, dialog, treeProcessor } = services;
        this.orm = orm;
        this.fieldService = fieldService;
        this.viewService = view;
        this.treeProcessor = treeProcessor;
        this.dialog = dialog;
        /** @type {string|false} */
        this.orderByCount = false;

        // used to manage search items related to date/datetime fields
        this.referenceMoment = DateTime.local();
        this.intervalOptions = getIntervalOptions();
        this.categoriesLoadId = 0;
        this.filtersLoadId = 0;
    }

    /**
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
     * @param {Object} [config.display]
     * @param {boolean} [config.display.searchPanel=true]
     * @param {OrderTerm[]} [config.orderBy=[]]
     * @param {string[]} [config.searchMenuTypes=["filter", "groupBy", "favorite"]]
     * @param {Object} [config.state]
     * @param {boolean} [config.hideCustomGroupBy]
     * @param {boolean} [config.canOrderByCount]
     * @param {string[]} [config.defaultGroupBy]
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

        this.globalContext = toRaw({ ...context });
        this.globalDomain = domain || [];
        this.globalGroupBy = groupBy || [];
        this.globalOrderBy = orderBy || [];
        this.hideCustomGroupBy = hideCustomGroupBy;

        this.searchMenuTypes = new Set(
            config.searchMenuTypes || ["filter", "groupBy", "favorite"],
        );
        this.canOrderByCount = config.canOrderByCount;
        this.defaultGroupBy = config.defaultGroupBy;

        const { irFilters, loadIrFilters, searchViewArch, searchViewId } = config;
        let { searchViewFields } = config;
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
                },
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
            this.__legacyParseSearchPanelArchAnyway(
                searchViewDescription,
                searchViewFields,
            );
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
            searchPanelDefaults,
        );
        const { labels, preSearchItems, searchPanelInfo, sections } = parser.parse();

        this.searchPanelInfo = {
            ...searchPanelInfo,
            loaded: false,
            shouldReload: false,
        };

        await Promise.all(labels.map((cb) => cb(this.orm)));

        // prepare search items (populate this.searchItems)
        for (const preGroup of preSearchItems || []) {
            this._createGroupOfSearchItems(preGroup);
        }
        this.nextGroupNumber =
            1 +
            Math.max(
                ...Object.values(this.searchItems).map((i) => i.groupNumber || 0),
                0,
            );

        const { dynamicFilters } = config;
        if (dynamicFilters) {
            this._createGroupOfDynamicFilters(dynamicFilters);
        }

        const defaultFavoriteId = this._createGroupOfFavorites(this.irFilters || []);
        const activateFavorite =
            "activateFavorite" in config ? config.activateFavorite : true;

        // activate default search items (populate this.query)
        this._activateDefaultSearchItems(activateFavorite ? defaultFavoriteId : null);

        // prepare search panel sections

        /** @type Map<number,Section> */
        this.sections = new Map(sections || []);
        this.display = this._getDisplay(config.display);

        if (this.display.searchPanel) {
            /** @type {DomainListRepr} */
            this.searchDomain = /** @type {DomainListRepr} */ (
                this._getDomain({ withSearchPanel: false })
            );
            this.sectionsPromise = this._fetchSections(
                this.categories,
                this.filters,
            ).then(() => {
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
            if (
                Object.keys(searchPanelDefaults).length ||
                this._shouldWaitForData(false)
            ) {
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

        this.globalContext = { ...context };
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
        return /** @type {Category[]} */ (
            [...this.sections.values()].filter((s) => s.type === "category")
        );
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
            this._domain = /** @type {DomainListRepr} */ (this._getDomain());
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
        return { ...this.globalContext, ...user.context };
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
        return /** @type {Filter[]} */ (
            [...this.sections.values()].filter((s) => s.type === "filter")
        );
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
     * @param {number} searchItemId
     * @param {Object} autocompleteValue
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
                queryElem.autocompleteValue.operator === operator,
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
     * Removes filter, field and favorite facets but keeps groupBy ones
     */
    clearFilters() {
        this.blockNotification = true;
        this.facets.forEach((facet) => {
            if (facet.type !== "groupBy") {
                this.deactivateGroup(facet.groupId);
            }
        });
        this.blockNotification = false;
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
                preFavorite.userIds.length === 1
                    ? FAVORITE_PRIVATE_GROUP
                    : FAVORITE_SHARED_GROUP,
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
        const serverSideIds = await this.orm.call("ir.filters", "create_filter", [
            irFilter,
        ]);
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
        const firstGroupBy = Object.values(this.searchItems).find(
            (f) => f.type === "groupBy",
        );
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
                {
                    type: "dateGroupBy",
                    defaultIntervalId: interval || DEFAULT_INTERVAL,
                },
                preSearchItem,
            );
            this.toggleDateGroupBy(this.nextId);
        } else {
            this.searchItems[this.nextId] = Object.assign(
                { type: "groupBy" },
                preSearchItem,
            );
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
        let sections = [...this.sections.values()].map((section) => ({
            ...section,
            empty: !hasValues(section),
        }));
        if (predicate) {
            sections = sections.filter(predicate);
        }
        return sections.sort((s1, s2) => s1.index - s2.index);
    }

    search() {
        this.trigger("update");
    }

    async splitAndAddDomain(domain, groupId) {
        return _splitAndAddDomain(this, domain, groupId);
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
        const index = this.query.findIndex(
            (queryElem) => queryElem.searchItemId === searchItemId,
        );
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
        const generatorIds = generatorId
            ? [generatorId]
            : searchItem.defaultGeneratorIds;
        for (const generatorId of generatorIds) {
            const index = this.query.findIndex(
                (queryElem) =>
                    queryElem.searchItemId === searchItemId &&
                    "generatorId" in queryElem &&
                    queryElem.generatorId === generatorId,
            );
            if (index >= 0) {
                this.query.splice(index, 1);
                if (!yearSelected(this._getSelectedGeneratorIds(searchItemId))) {
                    // This is the case where generatorId was the last option
                    // of type 'year' to be there before being removed above.
                    // Since other options of type 'month' or 'quarter' do
                    // not make sense without a year we deactivate all options.
                    this.query = this.query.filter(
                        (queryElem) => queryElem.searchItemId !== searchItemId,
                    );
                }
            } else {
                if (generatorId.startsWith("custom")) {
                    this.query = this.query.filter(
                        (queryElem) => searchItemId !== queryElem.searchItemId,
                    );
                    this.query.push({ searchItemId, generatorId });
                    continue;
                }
                this.query = this.query.filter(
                    (queryElem) =>
                        queryElem.searchItemId !== searchItemId ||
                        !queryElem.generatorId.startsWith("custom"),
                );
                this.query.push({ searchItemId, generatorId });
                if (!yearSelected(this._getSelectedGeneratorIds(searchItemId))) {
                    // Here we add 'year' as options if no option of type
                    // year is already selected.
                    const { defaultYearId } = getPeriodOptions(
                        this.referenceMoment,
                        searchItem.optionsParams,
                    ).find((o) => o.id === generatorId);
                    this.query.push({
                        searchItemId,
                        generatorId: defaultYearId,
                    });
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
                queryElem.intervalId === intervalId,
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
            title: _t("Custom Filter"),
            confirmButtonText: _t("Search"),
            discardButtonText: _t("Discard"),
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

    /** Generate search items for properties. Delegates to search_properties.js. */
    async getSearchItemsProperties(searchItem) {
        return _getSearchItemsProperties(this, searchItem);
    }

    //--------------------------------------------------------------------------
    // Private methods
    //--------------------------------------------------------------------------

    /** Lazily populate property-based search/group-by items. Delegates to search_properties.js. */
    async fillSearchViewItemsProperty() {
        return _fillSearchViewItemsProperty(this);
    }

    /** Fetch property definitions. Delegates to search_properties.js. */
    async _fetchPropertiesDefinition(resModel, fieldName) {
        return _fetchPropertiesDefinition(this, resModel, fieldName);
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
                ["dateGroupBy", "groupBy"].includes(
                    this.searchItems[item.searchItemId].type,
                ),
            )
        ) {
            this.orderByCount = false;
        }
    }

    /**
     * @param {number} sectionId
     * @param {Object} result
     */
    _createCategoryTree(sectionId, result) {
        const category = this.sections.get(sectionId);
        createCategoryTree(category, result, (cat, ids) =>
            this._ensureCategoryValue(cat, ids),
        );
    }

    /**
     * @param {number} sectionId
     * @param {Object} result
     */
    _createFilterTree(sectionId, result) {
        const filter = this.sections.get(sectionId);
        createFilterTree(filter, result);
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
        return enrichSearchItem(
            searchItem,
            this.query,
            this.referenceMoment,
            this.intervalOptions,
        );
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
        return extractSearchDefaults(this.globalContext);
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
        const categoriesLoadId = ++this.categoriesLoadId;
        await Promise.all(
            categories.map(async (category) => {
                const result = await this.orm
                    .cache({
                        type: "disk",
                        update: "always",
                        callback: (result, hasChanged) => {
                            if (
                                !hasChanged ||
                                categoriesLoadId !== this.categoriesLoadId
                            ) {
                                return;
                            }
                            this._createCategoryTree(category.id, result);
                            this._reset();
                            this.trigger("update");
                        },
                    })
                    .call(
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
                        },
                    );
                this._createCategoryTree(category.id, result);
            }),
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
        const filtersLoadId = ++this.filtersLoadId;
        await Promise.all(
            filters.map(async (filter) => {
                const result = await this.orm
                    .cache({
                        type: "disk",
                        update: "always",
                        callback: (result, hasChanged) => {
                            if (!hasChanged || filtersLoadId !== this.filtersLoadId) {
                                return;
                            }
                            this._createFilterTree(filter.id, result);
                            this._reset();
                            this.trigger("update");
                        },
                    })
                    .call(
                        this.resModel,
                        "search_panel_select_multi_range",
                        [filter.fieldName],
                        {
                            category_domain: categoryDomain,
                            comodel_domain: new Domain(filter.domain).toList(
                                evalContext,
                            ),
                            context: this.globalContext,
                            enable_counters: filter.enableCounters,
                            filter_domain: this._getFilterDomain(filter.id),
                            expand: filter.expand,
                            group_by: filter.groupBy || false,
                            group_domain: this._getGroupDomain(filter),
                            limit: filter.limit,
                            search_domain: searchDomain,
                        },
                    );
                this._createFilterTree(filter.id, result);
            }),
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
     * @param {number} [excludedCategoryId]
     * @returns {Array[]}
     */
    _getCategoryDomain(excludedCategoryId) {
        return computeCategoryDomain(
            this.categories,
            this.searchViewFields,
            excludedCategoryId,
        );
    }

    /**
     * Construct a single context from the contexts of
     * filters of type 'filter', 'favorite', and 'field'.
     * @returns {Object}
     */
    _getContext() {
        return computeSearchContext(this._getGroups(), user.context, (activeItem) =>
            this._getSearchItemContext(activeItem),
        );
    }

    /**
     * Compute the string representation or the description of the current domain associated
     * with a date filter starting from its corresponding query elements.
     */
    _getDateFilterDomain(dateFilter, generatorIds, key = "domain") {
        return computeDateFilterDomain(
            this.referenceMoment,
            dateFilter,
            generatorIds,
            key,
        );
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
        const withSearchPanel =
            ("withSearchPanel" in params ? params.withSearchPanel : true) &&
            this.display.searchPanel;
        const withGlobal = "withGlobal" in params ? params.withGlobal : true;
        return computeDomain({
            groups: this._getGroups(),
            globalDomain: this.globalDomain,
            withGlobal,
            withSearchPanel,
            getSearchItemDomain: (activeItem) => this._getSearchItemDomain(activeItem),
            getSearchPanelDomain: () => this._getSearchPanelDomain(),
            domainEvalContext: this.domainEvalContext,
            raw: params.raw,
        });
    }

    _getFacets() {
        return buildFacets({
            groups: this._getGroups(),
            searchItems: this.searchItems,
            getSearchItemDomain: (activeItem) => this._getSearchItemDomain(activeItem),
            getDateFilterDomain: (searchItem, generatorIds, key) =>
                this._getDateFilterDomain(searchItem, generatorIds, key),
            orderByCount: this.orderByCount,
            globalGroupBy: this.globalGroupBy,
            defaultGroupBy: this.defaultGroupBy,
            searchViewFields: this.searchViewFields,
            viewType: this.env.config.viewType,
        });
    }

    /**
     * Return the domain resulting from the combination of the autocomplete values
     * of a search item of type 'field'.
     */
    _getFieldDomain(field, autocompleteValues) {
        return computeFieldDomain(field, autocompleteValues);
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
     * @param {number} [excludedFilterId]
     * @returns {Array[]}
     */
    _getFilterDomain(excludedFilterId) {
        return computeFilterDomain(this.filters, excludedFilterId);
    }

    /**
     * Return the concatenation of groupBys comming from the active filters of
     * type 'favorite' and 'groupBy'.
     * The result respects the appropriate logic: the groupBys
     * coming from an active favorite (if any) come first, then come the
     * groupBys comming from the active filters of type 'groupBy' in the order
     * defined in this.query. If no groupBys are found, one tries to
     * find some groupBys in this.globalGroupBy or this.defaultGroupBy.
     * @param {Object} [options={}]
     * @param {boolean} [options.fallbackOnDefault=true]
     * @returns {string[]}
     */
    _getGroupBy(options = {}) {
        const fallbackOnDefault =
            "fallbackOnDefault" in options ? options.fallbackOnDefault : true;
        return computeGroupBy({
            groups: this._getGroups(),
            globalGroupBy: this.globalGroupBy,
            defaultGroupBy: this.defaultGroupBy,
            fallbackOnDefault,
            getSearchItemGroupBys: (activeItem) =>
                this._getSearchItemGroupBys(activeItem),
        });
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
        return computeGroupDomain(filter, this.searchViewFields);
    }

    /**
     * Reconstruct the (active) groups from the query elements.
     * @returns {Object[]}
     */
    _getGroups() {
        return getQueryGroups(this.query, this.searchItems);
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
        return buildIrFilterDescription({
            description,
            isDefault,
            isShared,
            embeddedActionId,
            localContext,
            localOrderBy,
            getContext: () => this._getContext(),
            getDomain: () => this._getDomain({ raw: true, withGlobal: false }),
            getGroupBy: () => this._getGroupBy(),
            getOrderBy: () => this._getOrderBy(),
            globalContext: this.globalContext,
            actionId: this.env.config.actionId,
            resModel: this.resModel,
        });
    }

    /**
     * @returns {OrderTerm[]}
     */
    _getOrderBy() {
        return computeOrderBy(
            this._getGroups(),
            this.searchItems,
            this.groupBy,
            this.orderByCount,
            this.globalOrderBy,
        );
    }

    /**
     * Return the context of the provided (active) filter.
     */
    _getSearchItemContext(activeItem) {
        return computeSearchItemContext(activeItem, this.searchItems);
    }

    /**
     * Return the domain of the provided filter.
     */
    _getSearchItemDomain(activeItem) {
        return computeSearchItemDomain(
            activeItem,
            this.searchItems,
            this.referenceMoment,
        );
    }

    _getSearchItemGroupBys(activeItem) {
        return computeSearchItemGroupBys(activeItem, this.searchItems);
    }

    /**
     * Starting from a date filter id, returns the array of option ids currently selected
     * for the corresponding date filter.
     */
    _getSelectedGeneratorIds(dateFilterId) {
        return getSelectedGeneratorIds(this.query, dateFilterId);
    }

    /**
     * @returns {Domain}
     */
    _getSearchPanelDomain() {
        return computeSearchPanelDomain(
            this._getCategoryDomain(),
            this._getFilterDomain(),
        );
    }

    /**
     * @param {Object} state
     */
    _importState(state) {
        execute(arrayToMap, state, this);
    }

    /**
     * @param {Object} irFilter
     */
    _irFilterToFavorite(irFilter) {
        return irFilterToFavorite(irFilter);
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
        reconciliateFavorites(
            this.searchItems,
            this.query,
            this.irFilters,
            (irFilter) => this._irFilterToFavorite(irFilter),
            (irFilters) => this._createGroupOfFavorites(irFilters),
        );
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
        const searchDomain = /** @type {DomainListRepr} */ (
            this._getDomain({ withSearchPanel: false })
        );
        const searchDomainChanged =
            this.searchPanelInfo.shouldReload ||
            JSON.stringify(this.searchDomain) !== JSON.stringify(searchDomain);
        this.searchDomain = searchDomain;

        // Check whether categories/filters will force a reload of the sections
        const toFetch = (section) =>
            section.enableCounters || (searchDomainChanged && !section.expand);
        const categoriesToFetch = this.categories.filter(toFetch);
        const filtersToFetch = this.filters.filter(toFetch);

        if (
            searchDomainChanged ||
            Boolean(categoriesToFetch.length + filtersToFetch.length)
        ) {
            if (this.display.searchPanel) {
                this.sectionsPromise = this._fetchSections(
                    categoriesToFetch,
                    filtersToFetch,
                );
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
        if (
            this.categories.length &&
            this.filters.some((filter) => filter.domain !== "[]")
        ) {
            // Selected category value might affect the filter values
            return true;
        }
        if (!this.searchDomain.length) {
            // No search domain -> no need to check for expand
            return false;
        }
        return [...this.sections.values()].some(
            (section) => !section.expand && searchDomainChanged,
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

        this.searchPanelInfo = {
            ...searchPanelInfo,
            loaded: false,
            shouldReload: false,
        };
    }
}
