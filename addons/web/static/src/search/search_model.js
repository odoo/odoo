// @ts-check
/** @odoo-module native */

import { EventBus, toRaw } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { makeLogger } from "@web/core/debug/debug_logger";
import { SearchModelEvent } from "@web/core/events";
import { DateTime } from "@web/core/l10n/luxon";
import { user } from "@web/core/user";
import { Mutex } from "@web/core/utils/concurrency";

import {
    DEFAULT_VIEWS_WITH_SEARCH_PANEL,
    SearchArchParser,
} from "./search_arch_parser.js";
import { computeSearchContext, computeSearchItemContext } from "./search_context.js";
import {
    computeCategoryDomain,
    computeDateFilterDescription,
    computeDateFilterDomain,
    computeDomain,
    computeFieldDomain,
    computeFilterDomain,
    computeGroupDomain,
    computeSearchItemDomain,
    computeSearchPanelDomain,
} from "./search_domain.js";
import { enrichSearchItem, indexQueryBySearchItem } from "./search_enrichment.js";
import { getFacets } from "./search_facets.js";
import { SearchFavoritesMixin } from "./search_favorites_mixin.js";
import {
    computeGroupBy,
    computeOrderBy,
    computeSearchItemGroupBys,
    getQueryGroups,
    getSelectedGeneratorIds,
} from "./search_group_by.js";
import { SearchPanelMixin } from "./search_panel/search_panel_mixin.js";
import { SearchPropertiesMixin } from "./search_properties_mixin.js";
import { SearchQueryMixin } from "./search_query_mixin.js";
import { SearchSplitDomainMixin } from "./search_split_domain_mixin.js";
import {
    isInvisible,
    itemsFromState,
    itemsToState,
    panelFromState,
    panelToState,
    propertiesFromState,
    propertiesToState,
    queryFromState,
    queryToState,
    SEARCH_MODEL_STATE_VERSION,
    takeSearchDefaults,
} from "./search_state.js";
import { getIntervalOptions } from "./utils/dates.js";

/** @import { Context } from "@web/core/context" */

/** @import { Domain, DomainListRepr } from "@web/core/domain" */

/** @import { OrderTerm } from "@web/core/utils/order_by" */

/** @import { Field, FieldInfo, SearchParams } from "@web/model/types" */

/** @import { ActiveItem, AutocompleteValue, Category, Facet, Filter, QueryElement, QueryGroup, SearchItem, SearchItems, Section, StoredSearchItem } from "./search_types" */

/**
 * @typedef {Object} SearchModelConfig
 * @property {string} resModel
 * @property {string} [searchViewArch]
 * @property {import("@web/views/ir/view_ir_schema").ViewIRNode} [searchViewIR]
 * @property {Record<string, any>} [searchViewFields]
 * @property {number|false} [searchViewId]
 * @property {Record<string, any>[]} [irFilters]
 * @property {boolean} [activateFavorite]
 * @property {Record<string, any>} [context]
 * @property {any[]} [domain]
 * @property {Record<string, any>[]} [dynamicFilters]
 * @property {string[]} [groupBy]
 * @property {boolean} [loadIrFilters]
 * @property {{controlPanel?: Record<string, any>|false, searchPanel?: boolean}} [display]
 * @property {OrderTerm[]} [orderBy]
 * @property {string[]} [searchMenuTypes]
 * @property {import("./search_state").SearchModelState} [state]
 * @property {boolean} [hideCustomGroupBy]
 * @property {boolean} [canOrderByCount]
 * @property {string[]} [defaultGroupBy]
 */

const log = makeLogger("web.search");

export class SearchModel extends SearchQueryMixin(
    SearchSplitDomainMixin(
        SearchFavoritesMixin(SearchPropertiesMixin(SearchPanelMixin(EventBus))),
    ),
) {
    /** @type {import("@web/env").OdooEnv & { config: Record<string, any> }} */
    env;

    /** @type {string} */
    resModel;
    /** @type {boolean | undefined} */
    blockNotification;

    /** @type {any[]} */
    globalDomain;

    /** @type {string[]} */
    globalGroupBy;

    /** @type {any[]} */
    globalOrderBy;

    /** @type {string[] | undefined} */
    defaultGroupBy;

    /** @type {Record<string, any>} */
    searchViewFields;

    /** @type {{ controlPanel: Object | false, searchPanel: boolean }} */
    display;

    /** @type {SearchItems} */
    searchItems;

    /** @type {number | false} */
    searchViewId;

    /** @type {QueryGroup[] | null} */
    _groups;
    _pendingNotification = false;
    _pendingTrigger = false;

    /**
     * @param {import("@web/env").OdooEnv} env
     * @param {Record<string, any>} services
     * @param {Record<string, any>} [args]
     */
    constructor(env, services, args) {
        super();
        this.env = /** @type {any} */ (env);
        this.setup(services, args);
    }

    /**
     * @param {Record<string, any>} services
     * @param {Record<string, any>} [_args]
     */
    setup(services, _args) {
        const {
            field: fieldService,
            orm,
            view,
            dialog,
            treeProcessor,
            DomainSelectorDialog,
            getDefaultDomain,
        } = services;
        this.orm = orm;
        this.fieldService = fieldService;
        this.viewService = view;
        this.treeProcessor = treeProcessor;
        this.dialog = dialog;
        this.DomainSelectorDialog = DomainSelectorDialog;
        this.getDefaultDomain = getDefaultDomain;
        /** @type {string|false} */
        this.orderByCount = false;

        this.referenceMoment = DateTime.local();
        this.intervalOptions = getIntervalOptions();
        /** @type {Map<number, number>} */
        this._sectionLoadIds = new Map();
        /** @type {Map<string, Section[]>|null} */
        this._sectionsByType = null;

        this._reloadMutex = new Mutex();
    }

    /** @param {SearchModelConfig} config */
    async load(config) {
        const { resModel } = config;
        if (!resModel) {
            throw Error(`SearchModel config should have a "resModel" key`);
        }
        this.resModel = resModel;
        this._reset();
        log.pipeline("load", () => ({
            resModel,
            searchViewId: config.searchViewId,
            fromState: Boolean(config.state),
            searchMenuTypes: config.searchMenuTypes,
        }));

        this._applyGlobalConfig(config);

        const { searchViewDescription, searchViewFields } =
            await this._resolveSearchView(config);

        const { searchDefaults, searchPanelDefaults } =
            this.takeSearchDefaultsFromGlobalContext();

        if (config.state) {
            return this._loadFromState(config);
        }
        return this._loadFromArch(config, {
            searchViewDescription,
            searchViewFields,
            searchDefaults,
            searchPanelDefaults,
        });
    }

    /** @param {SearchModelConfig} config */
    _applyGlobalConfig(config) {
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
        /** @type {boolean} */
        this.defaultGroupByRemoved = false;
        /** @type {any} */
        this._filledPropertyFields = undefined;
    }

    /**
     * @param {SearchModelConfig} config
     * @returns {Promise<{searchViewDescription: Record<string, any>, searchViewFields: Record<string, any>}>}
     */
    async _resolveSearchView(config) {
        const { irFilters, loadIrFilters, searchViewArch, searchViewIR, searchViewId } =
            config;
        let { searchViewFields } = config;
        const loadSearchView =
            searchViewId !== undefined &&
            ((!searchViewArch && !searchViewIR) ||
                !searchViewFields ||
                (!irFilters && loadIrFilters));

        const searchViewDescription = {};
        if (loadSearchView) {
            const result = await this.viewService.loadViews(
                {
                    context: this.globalContext,
                    resModel: this.resModel,
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
        if (searchViewArch || searchViewIR) {
            searchViewDescription.arch = searchViewArch;
            searchViewDescription.ir = searchViewIR;
        }
        if (irFilters) {
            searchViewDescription.irFilters = irFilters;
        }
        if (searchViewId !== undefined) {
            searchViewDescription.viewId = searchViewId;
        }

        this.searchViewFields = searchViewFields || {};
        if (searchViewDescription.irFilters) {
            this.irFilters = searchViewDescription.irFilters;
        }
        if (searchViewDescription.viewId !== undefined) {
            this.searchViewId = searchViewDescription.viewId;
        }
        return { searchViewDescription, searchViewFields };
    }

    /** @param {SearchModelConfig} config */
    async _loadFromState(config) {
        this._importState(config.state);
        if (this.defaultGroupByRemoved) {
            this.defaultGroupBy = undefined;
        }
        this.display = this._getDisplay(config.display);
        this._reconciliateFavorites();
        try {
            if (!this.searchPanelInfo.loaded) {
                await this._reloadSections();
            }
        } finally {
            this._pendingNotification = false;
        }
    }

    /**
     * @param {SearchModelConfig} config
     * @param {object} parts
     * @param {Record<string, any>} parts.searchViewDescription
     * @param {Record<string, any>} parts.searchViewFields
     * @param {Record<string, any>} parts.searchDefaults
     * @param {Record<string, any>} parts.searchPanelDefaults
     */
    async _loadFromArch(
        config,
        {
            searchViewDescription,
            searchViewFields,
            searchDefaults,
            searchPanelDefaults,
        },
    ) {
        await this._withNotificationsBlockedAsync(async () => {
            /** @type {Record<number, any>} */
            this.searchItems = {};
            /** @type {QueryElement[]} */
            this.query = [];

            this.nextId = 1;
            this.nextGroupId = 1;
            this.nextGroupNumber = 1;

            const parser = new SearchArchParser(
                searchViewDescription,
                searchViewFields,
                searchDefaults,
                searchPanelDefaults,
                this.domainEvalContext,
            );
            const { labels, preSearchItems, searchPanelInfo, sections } =
                parser.parse();

            this.searchPanelInfo = {
                ...searchPanelInfo,
                loaded: false,
                shouldReload: false,
            };

            await Promise.all(labels.map((cb) => cb(this.orm)));

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

            const defaultFavoriteId = this._createGroupOfFavorites(
                this.irFilters || [],
            );
            const activateFavorite =
                "activateFavorite" in config ? config.activateFavorite : true;

            this._activateDefaultSearchItems(
                activateFavorite ? defaultFavoriteId : null,
            );

            this.sections = new Map(
                /** @type {[number, Section][]} */ (sections || []),
            );
            this.display = this._getDisplay(config.display);

            if (this.display.searchPanel) {
                await this._initSearchPanel(searchPanelDefaults);
            }
        });
        this._pendingNotification = false;
    }

    /**
     * @param {object} [config={}]
     * @param {Record<string, any>} [config.context={}]
     * @param {any[]} [config.domain=[]]
     * @param {string[]} [config.groupBy=[]]
     * @param {OrderTerm[]} [config.orderBy=[]]
     */
    async reload(config = {}) {
        this._reset();
        log.pipeline("reload", () => ({
            resModel: this.resModel,
            keys: Object.keys(config),
        }));

        const { context, domain, groupBy, orderBy } = config;

        this.globalContext =
            "context" in config ? toRaw({ ...(context || {}) }) : this.globalContext;
        this.globalDomain = "domain" in config ? domain || [] : this.globalDomain;
        this.globalGroupBy = "groupBy" in config ? groupBy || [] : this.globalGroupBy;
        this.globalOrderBy = "orderBy" in config ? orderBy || [] : this.globalOrderBy;

        this.takeSearchDefaultsFromGlobalContext();

        await this._reloadSections();
        await this._drainPendingNotification();
    }

    /** @returns {Category[]} */
    get categories() {
        return /** @type {Category[]} */ (this._sectionsOfType("category"));
    }

    /**
     * @param {string} type
     * @returns {Section[]}
     */
    _sectionsOfType(type) {
        this._sectionsByType ??= new Map();
        let sections = this._sectionsByType.get(type);
        if (!sections) {
            sections = [...this.sections.values()].filter((s) => s.type === type);
            this._sectionsByType.set(type, sections);
        }
        return sections;
    }

    /** @returns {Context} */
    get _rawContext() {
        if (!this._context) {
            this._context = makeContext([this.globalContext, this._getContext()]);
            this._freezeInDevMode(this._context);
        }
        return this._context;
    }

    /** @returns {Context} */
    get context() {
        return this._rawContext;
    }

    /** @returns {DomainListRepr} */
    get domain() {
        if (!this._domain) {
            this._domain = /** @type {DomainListRepr} */ (this._getDomain());
            this._freezeInDevMode(this._domain);
        }
        return this._domain;
    }

    /** @returns {string} */
    get domainString() {
        return this._getDomain({ raw: true }).toString();
    }

    get domainEvalContext() {
        return { ...this.globalContext, ...user.context };
    }

    get facets() {
        if (!this._facets) {
            const facets = [];
            for (const facet of this._getFacets()) {
                if (facet.type === "groupBy" && !this.searchMenuTypes.has(facet.type)) {
                    continue;
                }
                facets.push(facet);
            }
            this._facets = this._freezeInDevMode(facets);
        }
        return this._facets;
    }

    /** @returns {Filter[]} */
    get filters() {
        return /** @type {Filter[]} */ (this._sectionsOfType("filter"));
    }

    /** @returns {string[]} */
    get groupBy() {
        if (!this._groupBy) {
            this._groupBy = this._getGroupBy();
        }
        return this._groupBy.slice();
    }

    /** @returns {OrderTerm[]} */
    get orderBy() {
        if (!this._orderBy) {
            this._orderBy = this._getOrderBy();
            this._freezeInDevMode(this._orderBy);
        }
        return this._orderBy;
    }

    get isDebugMode() {
        return !!this.env.debug;
    }

    /** @returns {import("./search_state").SearchModelState} */
    exportState() {
        return /** @type {import("./search_state").SearchModelState} */ ({
            version: SEARCH_MODEL_STATE_VERSION,
            ...queryToState(this),
            ...itemsToState(this),
            ...panelToState(this),
            ...propertiesToState(this),
        });
    }

    /**
     * @param {(searchItem: Object) => boolean} [predicate]
     * @returns {Record<string, any>[]}
     */
    getSearchItems(predicate) {
        if (!this._enrichedSearchItems) {
            const domainEvalContext = this.domainEvalContext;
            const queryIndex = indexQueryBySearchItem(this.query);
            const enrichedSearchItems = [];
            for (const searchItem of Object.values(this.searchItems)) {
                if (isInvisible(searchItem.invisible, domainEvalContext)) {
                    continue;
                }
                enrichedSearchItems.push(this._enrichItem(searchItem, queryIndex));
            }
            enrichedSearchItems.sort(
                (f1, f2) =>
                    (f1.groupNumber || 0) - (f2.groupNumber || 0) || f1.id - f2.id,
            );
            this._enrichedSearchItems = enrichedSearchItems;
        }
        return predicate
            ? this._enrichedSearchItems.filter(predicate)
            : [...this._enrichedSearchItems];
    }

    search() {
        this._reset();
        log.logic("search", () => ({
            resModel: this.resModel,
            query: this.query.length,
        }));
        this.trigger(SearchModelEvent.UPDATE);
    }

    /** @returns {Promise<void>} */
    async refresh() {
        return this._notify();
    }

    /** @param {Record<string, any>[]} dynamicFilters */
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

    /** @param {Record<string, any>[]} pregroup */
    _createGroupOfSearchItems(pregroup) {
        pregroup.forEach((/** @type {Record<string, any>} */ preSearchItem) => {
            const searchItem = Object.assign(preSearchItem, {
                groupId: this.nextGroupId,
                id: this.nextId,
            });
            this.searchItems[this.nextId] = /** @type {StoredSearchItem} */ (
                searchItem
            );
            this.nextId++;
        });
        this.nextGroupId++;
        this._enrichedSearchItems = null;
    }

    /**
     * @param {StoredSearchItem} searchItem
     * @param {Map<number, QueryElement[]>} queryIndex
     */
    _enrichItem(searchItem, queryIndex) {
        return enrichSearchItem(
            searchItem,
            queryIndex,
            this.referenceMoment,
            this.intervalOptions,
        );
    }

    takeSearchDefaultsFromGlobalContext() {
        return takeSearchDefaults(this.globalContext);
    }

    /**
     * @param {number} [excludedCategoryId]
     * @returns {any[][]}
     */
    _getCategoryDomain(excludedCategoryId) {
        return computeCategoryDomain(
            this.categories,
            this.searchViewFields,
            excludedCategoryId,
        );
    }

    /** @returns {Record<string, any>} */
    _getContext() {
        return computeSearchContext(
            this._getGroups(),
            user.context,
            (/** @type {ActiveItem} */ activeItem) =>
                this._getSearchItemContext(activeItem),
        );
    }

    /**
     * @param {SearchItem} dateFilter
     * @param {string[]} generatorIds
     * @returns {Domain}
     */
    _getDateFilterDomain(dateFilter, generatorIds) {
        return computeDateFilterDomain(this.referenceMoment, dateFilter, generatorIds);
    }

    /**
     * @param {SearchItem} dateFilter
     * @param {string[]} generatorIds
     * @returns {string}
     */
    _getDateFilterDescription(dateFilter, generatorIds) {
        return computeDateFilterDescription(
            this.referenceMoment,
            dateFilter,
            generatorIds,
        );
    }

    /**
     * @private
     * @param {Record<string, any>} [display={}]
     * @returns {{ controlPanel: Object | false, searchPanel: boolean }}
     */
    _getDisplay(display = {}) {
        const { viewTypes } = this.searchPanelInfo;
        const { viewType } = this.env.config;
        return {
            controlPanel: "controlPanel" in display ? display.controlPanel : {},
            searchPanel: Boolean(
                this.sections.size &&
                (!viewType || viewTypes.includes(viewType)) &&
                ("searchPanel" in display ? display.searchPanel : true),
            ),
        };
    }

    /**
     * @param {object} [params]
     * @param {boolean} [params.raw=false]
     * @param {boolean} [params.withSearchPanel=true]
     * @param {boolean} [params.withGlobal=true]
     * @returns {DomainListRepr | Domain}
     */
    _getDomain(params = {}) {
        const withSearchPanel =
            (params.withSearchPanel ?? true) && this.display.searchPanel;
        const withGlobal = params.withGlobal ?? true;
        return computeDomain({
            groups: this._getGroups(),
            globalDomain: this.globalDomain,
            withGlobal,
            withSearchPanel,
            getSearchItemDomain: (/** @type {ActiveItem} */ activeItem) =>
                this.getSearchItemDomain(activeItem),
            getSearchPanelDomain: () => this._getSearchPanelDomain(),
            domainEvalContext: this.domainEvalContext,
            raw: params.raw,
        });
    }

    _getFacets() {
        return getFacets({
            groups: this._getGroups(),
            searchItems: this.searchItems,
            getSearchItemDomain: (/** @type {ActiveItem} */ activeItem) =>
                this.getSearchItemDomain(activeItem),
            getDateFilterDescription: (
                /** @type {SearchItem} */ searchItem,
                /** @type {string[]} */ generatorIds,
            ) => this._getDateFilterDescription(searchItem, generatorIds),
            orderByCount: this.orderByCount,
            globalGroupBy: this.globalGroupBy,
            defaultGroupBy: this.defaultGroupBy,
            searchViewFields: this.searchViewFields,
            viewType: this.env.config.viewType,
        });
    }

    /**
     * @param {SearchItem} field
     * @param {AutocompleteValue[]} autocompleteValues
     */
    _getFieldDomain(field, autocompleteValues) {
        return computeFieldDomain(field, autocompleteValues);
    }

    /**
     * @param {number} [excludedFilterId]
     * @returns {any[][]}
     */
    _getFilterDomain(excludedFilterId) {
        return computeFilterDomain(this.filters, excludedFilterId);
    }

    /**
     * @param {object} [options={}]
     * @param {boolean} [options.fallbackOnDefault=true]
     * @returns {string[]}
     */
    _getGroupBy(options = {}) {
        if (!this.searchMenuTypes.has("groupBy")) {
            return [];
        }
        const fallbackOnDefault = options.fallbackOnDefault ?? true;
        return computeGroupBy({
            groups: this._getGroups(),
            globalGroupBy: this.globalGroupBy,
            defaultGroupBy: this.defaultGroupBy,
            fallbackOnDefault,
            getSearchItemGroupBys: (/** @type {ActiveItem} */ activeItem) =>
                this._getSearchItemGroupBys(activeItem),
        });
    }

    /**
     * @param {Filter} filter
     * @returns {Record<string, any[][]> | any[][] | null}
     */
    _getGroupDomain(filter) {
        return computeGroupDomain(filter, this.searchViewFields);
    }

    /** @returns {QueryGroup[]} */
    _getGroups() {
        if (!this._groups) {
            this._groups = getQueryGroups(this.query, this.searchItems);
        }
        return this._groups;
    }

    /** @returns {OrderTerm[]} */
    _getOrderBy() {
        return computeOrderBy(
            this._getGroups(),
            this.searchItems,
            this._getGroupBy(),
            this.orderByCount,
            this.globalOrderBy,
        );
    }

    /** @param {ActiveItem} activeItem */
    _getSearchItemContext(activeItem) {
        return computeSearchItemContext(activeItem, this.searchItems);
    }

    /** @param {ActiveItem} activeItem */
    getSearchItemDomain(activeItem) {
        return computeSearchItemDomain(
            activeItem,
            this.searchItems,
            this.referenceMoment,
            {
                getFieldDomain: (field, autocompleteValues) =>
                    this._getFieldDomain(field, autocompleteValues),
                getDateFilterDomain: (dateFilter, generatorIds) =>
                    this._getDateFilterDomain(dateFilter, generatorIds),
            },
        );
    }

    /** @param {ActiveItem} activeItem */
    _getSearchItemGroupBys(activeItem) {
        return computeSearchItemGroupBys(activeItem, this.searchItems);
    }

    /** @param {number} dateFilterId */
    _getSelectedGeneratorIds(dateFilterId) {
        return getSelectedGeneratorIds(this.query, dateFilterId);
    }

    /** @returns {Domain} */
    _getSearchPanelDomain() {
        return computeSearchPanelDomain(
            this._getCategoryDomain(),
            this._getFilterDomain(),
        );
    }

    /** @param {import("./search_state").SearchModelState} state */
    _importState(state) {
        if (
            state.version !== undefined &&
            state.version !== SEARCH_MODEL_STATE_VERSION
        ) {
            console.warn(
                `[search] importing a search state of unknown version ${state.version} ` +
                    `(this build writes ${SEARCH_MODEL_STATE_VERSION}); ` +
                    "importing the known keys on a best-effort basis",
            );
        }
        queryFromState(state, this);
        itemsFromState(state, this);
        panelFromState(state, this);
        propertiesFromState(state, this);
        if (!this.searchPanelInfo) {
            this.searchPanelInfo = {
                className: "",
                viewTypes: [...DEFAULT_VIEWS_WITH_SEARCH_PANEL],
                loaded: false,
                shouldReload: false,
            };
        }
    }

    /** @param {{ reloadSections?: boolean }} [options] */
    async _notify({ reloadSections = true } = {}) {
        this._reset();

        if (this.blockNotification) {
            if (reloadSections) {
                this._pendingNotification = true;
            } else {
                this._pendingTrigger = true;
            }
            return;
        }

        if (reloadSections) {
            do {
                this._pendingNotification = false;
                await this._reloadSections();
            } while (this._pendingNotification);
        }
        this._pendingTrigger = false;
        log.logic("notify", () => ({
            resModel: this.resModel,
            reloadSections,
            domain: this.domain,
            groupBy: this.groupBy,
            orderBy: this.orderBy,
        }));

        this.trigger(SearchModelEvent.UPDATE);
    }

    /**
     * @template T
     * @param {() => T} fn
     * @returns {T}
     */
    _withNotificationsBlocked(fn) {
        /** @type {boolean | undefined} */
        const wasBlocked = this.blockNotification;
        this.blockNotification = true;
        try {
            return fn();
        } finally {
            this.blockNotification = wasBlocked;
        }
    }

    /**
     * @template T
     * @param {() => Promise<T>} fn
     * @returns {Promise<T>}
     */
    async _withNotificationsBlockedAsync(fn) {
        /** @type {boolean | undefined} */
        const wasBlocked = this.blockNotification;
        this.blockNotification = true;
        try {
            return await fn();
        } finally {
            this.blockNotification = wasBlocked;
        }
    }

    /** @returns {Promise<void>} */
    async _drainPendingNotification() {
        if (this.blockNotification) {
            return;
        }
        if (this._pendingNotification) {
            this._pendingNotification = false;
            await this._notify();
        } else if (this._pendingTrigger) {
            this._pendingTrigger = false;
            this.trigger(SearchModelEvent.UPDATE);
        }
    }

    /**
     * @template T
     * @param {T} value
     * @returns {T}
     */
    _freezeInDevMode(value) {
        if (this.isDebugMode) {
            Object.freeze(value);
        }
        return value;
    }

    _reset() {
        this._context = null;
        this._domain = null;
        this._groupBy = null;
        this._orderBy = null;
        this._groups = null;
        this._facets = null;
        this._enrichedSearchItems = null;
        this._sections = null;
        this._sectionsByType = null;
    }
}
