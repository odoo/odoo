import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { DataPoint } from "@web/model/relational_model/datapoint";
import { Record as RelationalRecord } from "@web/model/relational_model/record";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { getFieldsSpec } from "@web/model/relational_model/utils";
import { orderByToString } from "@web/search/utils/order_by";

/**
 * Key used by `hierarchy_read` to store the child ids when no child field is
 * given to the view.
 */
const DEFAULT_CHILD_FIELD_NAME = "__child_ids__";

/**
 * Get the id of the given many2one field value
 *
 * @param {false | { id: number }} value many2one value
 * @returns {false | number} id of the many2one
 */
function getIdOfMany2oneField(value) {
    return (value && value.id) || false;
}

/**
 * Record displayed in the hierarchy view.
 *
 * It doesn't store any structural information: the parent/children relations
 * live in the root (@see HierarchyRoot), the record only reads them.
 */
export class HierarchyRecord extends RelationalRecord {
    /**
     * @returns {number | false}
     */
    get parentResId() {
        return this.model.root.parentIds[this.resId] || false;
    }

    /**
     * @returns {HierarchyRecord | undefined} parent record if it is loaded
     */
    get parentRecord() {
        return this.model.root.getParentRecord(this.resId);
    }

    /**
     * @returns {number[]} res ids of all known children (loaded or not)
     */
    get childResIds() {
        return this.model.root.childIds[this.resId] || [];
    }

    /**
     * @returns {HierarchyRecord[]} loaded children
     */
    get childRecords() {
        return this.model.root.getChildRecords(this.resId);
    }

    get hasChildren() {
        return this.childResIds.length > 0;
    }

    /**
     * @returns {boolean} true if the children of the record are displayed
     */
    get isExpanded() {
        return this.model.root.expandedPath.at(-1) === this.resId;
    }

    toggleChildren() {
        return this.isExpanded ? this.model.collapse(this) : this.model.expand(this);
    }
}

/**
 * Root datapoint of the hierarchy model.
 *
 * The hierarchy is stored flat: a map of records indexed by res id, and
 * adjacency maps (parent per record, children per record). The displayed part
 * of the hierarchy is described by `expandedPath`, the res ids from a root to
 * the record whose children are displayed.
 */
export class HierarchyRoot extends DataPoint {
    /**
     * @param {Object} _config
     * @param {Object[]} data records data returned by the server
     */
    setup(_config, data) {
        /** @type {Record<number, HierarchyRecord>} */
        this.records = {};
        /** @type {Record<number, number | false>} */
        this.parentIds = {};
        /** @type {Record<number, number[]>} */
        this.childIds = {};
        /** @type {number[]} */
        this.expandedPath = [];
        /** @type {number[]} res ids in loading order */
        this._resIds = [];
        this._addRecords(data);
    }

    get hasData() {
        return this._resIds.length > 0;
    }

    /**
     * @returns {number[]} res ids of all loaded records
     */
    get resIds() {
        return [...this._resIds];
    }

    /**
     * @returns {HierarchyRecord[]} records whose parent is not loaded
     */
    get rootRecords() {
        let resIds = this._resIds.filter((resId) => !this.records[this.parentIds[resId]]);
        if (!resIds.length) {
            // all loaded records are part of a cycle, display them all
            resIds = this._resIds;
        }
        return resIds.map((resId) => this.records[resId]);
    }

    /**
     * @returns {HierarchyRecord | null} record whose children are displayed
     */
    get expandedRecord() {
        return this.records[this.expandedPath.at(-1)] || null;
    }

    /**
     * @returns {HierarchyRecord[]} records to display in the view
     */
    get displayedRecords() {
        const expandedRecord = this.expandedRecord;
        return expandedRecord ? this.getChildRecords(expandedRecord.resId) : this.rootRecords;
    }

    /**
     * @param {number} resId
     * @returns {HierarchyRecord[]} loaded children of the given record
     */
    getChildRecords(resId) {
        return (this.childIds[resId] || []).map((id) => this.records[id]).filter(Boolean);
    }

    /**
     * @param {number} resId
     * @returns {HierarchyRecord | undefined}
     */
    getParentRecord(resId) {
        return this.records[this.parentIds[resId]];
    }

    /**
     * Get the res ids of the loaded ancestors of a record.
     *
     * @param {number} resId
     * @returns {number[]} ancestor res ids, from the root to the direct parent
     */
    getAncestorIds(resId) {
        const ancestorIds = [];
        const visited = new Set([resId]);
        let parentId = this.parentIds[resId];
        while (this.records[parentId] && !visited.has(parentId)) {
            visited.add(parentId);
            ancestorIds.unshift(parentId);
            parentId = this.parentIds[parentId];
        }
        return ancestorIds;
    }

    /**
     * Compute the path to expand after a load: descend from the roots as long
     * as a record has loaded children.
     *
     * @returns {number[]}
     */
    _computeExpandedPath() {
        const path = [];
        const visited = new Set();
        let candidates = this.rootRecords;
        while (true) {
            const record = candidates.find(
                (r) => !visited.has(r.resId) && this.getChildRecords(r.resId).length
            );
            if (!record) {
                return path;
            }
            visited.add(record.resId);
            path.push(record.resId);
            candidates = this.getChildRecords(record.resId);
        }
    }

    /**
     * Create (or update) the records and the adjacency maps from server data.
     *
     * @param {Object[]} data
     */
    _addRecords(data) {
        for (const recordData of data) {
            const resId = recordData.id;
            if (this.records[resId]) {
                this.records[resId]._applyValues(recordData);
            } else {
                this.records[resId] = this.model._createRecordDatapoint(recordData);
                this._resIds.push(resId);
            }
            this.parentIds[resId] = getIdOfMany2oneField(
                recordData[this.model.parentFieldName]
            );
            const childIds = this.model._extractChildIds(recordData);
            if (childIds) {
                this.childIds[resId] = childIds;
            }
        }
        for (const { id: resId } of data) {
            const parentId = this.parentIds[resId];
            if (parentId) {
                this.childIds[parentId] ||= [];
                if (!this.childIds[parentId].includes(resId)) {
                    this.childIds[parentId].push(resId);
                }
            }
        }
    }

    /**
     * Remove a record from the children of its current parent.
     *
     * @param {number} resId
     */
    _detachFromParent(resId) {
        const parentId = this.parentIds[resId];
        if (parentId && this.childIds[parentId]) {
            this.childIds[parentId] = this.childIds[parentId].filter((id) => id !== resId);
        }
        this.parentIds[resId] = false;
    }
}

export class HierarchyModelTest extends RelationalModel {
    static Record = HierarchyRecord;
    static HierarchyRoot = HierarchyRoot;
    static withCache = false;

    setup(params, services) {
        const config = {
            resModel: params.resModel,
            fields: params.fields,
            activeFields: params.activeFields,
            domain: [],
            orderBy: [],
            ...params.config,
            groupBy: [],
            isMonoRecord: false,
        };
        super.setup({ ...params, config }, services);
        this.parentFieldName = params.parentFieldName;
        this.childFieldName = params.childFieldName;
        // the child field only feeds the adjacency maps, the records don't need it
        const { [this.childFieldName]: _childField, ...recordActiveFields } =
            this.config.activeFields;
        this.recordActiveFields = recordActiveFields;
    }

    /**
     * @returns {number[]} res ids of all loaded records
     */
    get resIds() {
        return this.root?.resIds || [];
    }

    /**
     * Get default domain to use, when no domain is given in the config
     *
     * @returns {import("@web/core/domain").DomainListRepr}
     */
    get defaultDomain() {
        return [[this.parentFieldName, "=", false]];
    }

    /**
     * Get the global domain of the view (which is the domain defined on the
     * view without applying filters).
     *
     * @returns {import("@web/core/domain").DomainListRepr}
     */
    get globalDomain() {
        if (!this.env.searchModel?.globalDomain.length) {
            return [];
        }
        return new Domain(this.env.searchModel.globalDomain).toList(
            this.env.searchModel.domainEvalContext
        );
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    exportState() {
        const state = super.exportState();
        state.config = {
            ...state.config,
            resIds: this.root.resIds,
            expandedPath: [...this.root.expandedPath],
        };
        return state;
    }

    /**
     * @override
     */
    async load(params = {}) {
        const { resIds, expandedPath, ...config } = this._getNextConfig(this.config, params);
        this.hooks.onWillLoadRoot(config);
        const data = await this.keepLast.add(this._loadData(config, resIds));
        this.root = this._createRoot(config, data, expandedPath);
        this.config = config;
        await this.hooks.onRootLoaded(this.root);
        this.notify();
    }

    /**
     * Reload the current view with all currently loaded records
     */
    async reload() {
        const data = await this.keepLast.add(this._loadData(this.config, this.root.resIds));
        this.root = this._createRoot(this.config, data, this.root.expandedPath);
        this.notify();
    }

    /**
     * @override
     * Each notify can specify a scroll target (default is to not scroll, as
     * records notify the model without payload when they are updated).
     */
    notify(payload = { scrollTarget: "none" }) {
        super.notify();
        this.bus.trigger("hierarchyScrollTarget", payload);
    }

    /**
     * Display the children of the given record, fetching the missing ones.
     *
     * @param {HierarchyRecord} record
     */
    async expand(record) {
        if (!record.hasChildren) {
            return;
        }
        const childResIds = record.childResIds;
        const missingResIds = childResIds.filter((resId) => !this.root.records[resId]);
        if (missingResIds.length) {
            const data = await this.keepLast.add(this._fetchRecords(missingResIds));
            this.root._addRecords(data);
            if (missingResIds.length === childResIds.length) {
                // keep the order given by the server
                this.root.childIds[record.resId] = data.map((d) => d.id);
            }
        }
        this.root.expandedPath = [...this.root.getAncestorIds(record.resId), record.resId];
        this.notify({ scrollTarget: "bottom" });
    }

    /**
     * Hide the children of the given record.
     *
     * @param {HierarchyRecord} record
     */
    collapse(record) {
        const index = this.root.expandedPath.indexOf(record.resId);
        if (index !== -1) {
            this.root.expandedPath = this.root.expandedPath.slice(0, index);
            this.notify({ scrollTarget: "bottom" });
        }
    }

    /**
     * ORM call to update the parentId of a record during @see updateParentNode
     * Can be overridden to not use "write".
     *
     * @param {HierarchyRecord} record record which parentId should be changed
     * @param {number | false} parentResId id of the new parent record
     */
    async updateParentId(record, parentResId = false) {
        return this.orm.write(
            this.config.resModel,
            [record.resId],
            { [this.parentFieldName]: parentResId },
            { context: this.config.context }
        );
    }

    /**
     * @param {number | string} resId of the record to update
     * @param {Object} parentInfo
     * @param {number | string} [parentInfo.parentNodeId] resId of the new parent (from the DOM)
     * @param {number | false} [parentInfo.parentResId] resId of the new parent
     */
    async updateParentNode(resId, { parentNodeId, parentResId } = {}) {
        const root = this.root;
        const record = root.records[resId];
        if (!record) {
            return;
        }
        parentResId = Number(parentNodeId) || parentResId || false;
        const parentRecord = root.records[parentResId];
        if (
            parentResId === record.parentResId ||
            (parentRecord && !this.validateUpdateParentNode(record, parentRecord))
        ) {
            return;
        }
        await this.mutex.exec(() => this.updateParentId(record, parentResId));
        // Reload the moved record and its new siblings.
        const { records: data } = await this.orm.webSearchRead(
            this.config.resModel,
            this.computeUpdateParentNodeDomain(record, parentResId),
            {
                specification: this._getFieldsSpec(),
                context: this.config.context,
                order: orderByToString(this.config.orderBy),
            }
        );
        if (!data.length) {
            return this.reload();
        }
        // Validate that data coming from the server is still compatible with the current
        // configuration of the hierarchy.
        if (data.some((d) => getIdOfMany2oneField(d[this.parentFieldName]) !== parentResId)) {
            this.notification.add(
                _t(
                    `The parent of "%s" was successfully updated. Reloading records to account for other changes.`,
                    record.data.display_name || record.data.name
                ),
                { type: "success" }
            );
            return this.reload();
        }
        if (!this.childFieldName) {
            await this._fetchChildIds(data);
        }
        root._detachFromParent(record.resId);
        root._addRecords(data);
        if (parentResId) {
            root.childIds[parentResId] = data.map((d) => d.id);
        }
        root.expandedPath = parentRecord ? [...root.getAncestorIds(parentResId), parentResId] : [];
        this.notify({ scrollTarget: record.resId });
    }

    /**
     * @param {HierarchyRecord} record
     * @param {HierarchyRecord} parentRecord
     * @returns {boolean}
     */
    validateUpdateParentNode(record, parentRecord) {
        if (parentRecord.resId === record.resId) {
            this.notification.add(_t("The parent record cannot be the record dragged."), {
                type: "danger",
            });
            return false;
        } else if (this.root.getAncestorIds(parentRecord.resId).includes(record.resId)) {
            this.notification.add(_t("Cannot change the parent because it will cause a cyclic."), {
                type: "danger",
            });
            return false;
        }
        return true;
    }

    /**
     * Returns a domain to get the moved record and all children of its new
     * parent (for ordering).
     *
     * @param {HierarchyRecord} record that is moving
     * @param {number | false} parentResId resId of the new parent
     * @returns {import("@web/core/domain").DomainListRepr}
     */
    computeUpdateParentNodeDomain(record, parentResId) {
        let domain = Domain.or([
            [["id", "=", record.resId]],
            [[this.parentFieldName, "=", parentResId]],
        ]);
        const globalDomain = this.globalDomain;
        if (globalDomain.length) {
            domain = Domain.and([domain, globalDomain]);
        }
        return domain.toList({});
    }

    /**
     * Evaluate if the current search query is the default one.
     *
     * @returns {boolean}
     */
    isSearchDefaultOrEmpty() {
        if (!this.env.searchModel) {
            return true;
        }
        const isDisabledOptionalSearchMenuType = (type) =>
            ["filter", "groupBy", "favorite"].includes(type) &&
            !this.env.searchModel.searchMenuTypes.has(type);
        const activeSearchItems = this.env.searchModel.getSearchItems(
            (item) => item.isActive && !isDisabledOptionalSearchMenuType(item.type)
        );
        if (!activeSearchItems.length) {
            return true;
        }
        const defaultSearchItems = this.env.searchModel.getSearchItems(
            (item) =>
                item.isDefault &&
                item.type !== "favorite" &&
                !isDisabledOptionalSearchMenuType(item.type)
        );
        return JSON.stringify(defaultSearchItems) === JSON.stringify(activeSearchItems);
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    /**
     * @param {Object} config
     * @param {Object[]} data
     * @param {number[]} [expandedPath] path to restore, computed from data if not given
     * @returns {HierarchyRoot}
     */
    _createRoot(config, data, expandedPath) {
        const root = new this.constructor.HierarchyRoot(this, config, data);
        root.expandedPath = expandedPath
            ? expandedPath.filter((resId) => root.records[resId])
            : root._computeExpandedPath();
        return root;
    }

    /**
     * @param {Object} data
     * @returns {HierarchyRecord}
     */
    _createRecordDatapoint(data) {
        return new this.constructor.Record(
            this,
            {
                context: this.config.context,
                activeFields: this.recordActiveFields,
                resModel: this.config.resModel,
                fields: this.config.fields,
                resId: data.id,
                resIds: [data.id],
                isMonoRecord: true,
                mode: "readonly",
            },
            data
        );
    }

    /**
     * @param {Object} data
     * @returns {number[] | null} child res ids given by the server, if any
     */
    _extractChildIds(data) {
        const value = data[this.childFieldName || DEFAULT_CHILD_FIELD_NAME];
        if (!Array.isArray(value)) {
            return null;
        }
        return value.map((v) => (typeof v === "number" ? v : v.id));
    }

    /**
     * Fetch the child ids of the given records, when no child field is given
     * to the view.
     *
     * @param {Object[]} data
     */
    async _fetchChildIds(data) {
        const resIds = data.map((d) => d.id);
        if (!resIds.length) {
            return;
        }
        const groups = await this.orm.formattedReadGroup(
            this.config.resModel,
            [[this.parentFieldName, "in", resIds]],
            [this.parentFieldName],
            ["id:array_agg"],
            {
                context: this.config.context,
                order: orderByToString(this.config.orderBy),
            }
        );
        const childIdsPerId = Object.fromEntries(
            groups.map((g) => [g[this.parentFieldName][0], g["id:array_agg"]])
        );
        for (const d of data) {
            d[DEFAULT_CHILD_FIELD_NAME] = childIdsPerId[d.id] || [];
        }
    }

    /**
     * @param {number[]} resIds
     * @returns {Promise<Object[]>}
     */
    async _fetchRecords(resIds) {
        const { records } = await this.orm.webSearchRead(
            this.config.resModel,
            [["id", "in", resIds]],
            {
                specification: this._getFieldsSpec(),
                context: this.config.context,
                order: orderByToString(this.config.orderBy),
            }
        );
        if (!this.childFieldName) {
            await this._fetchChildIds(records);
        }
        return records;
    }

    _getFieldsSpec(context = this.config.context) {
        return getFieldsSpec(this.config.activeFields, this.config.fields, context);
    }

    /**
     * Get the next model config to use
     *
     * @param {Object} currentConfig current model config used
     * @param {Object} params new params
     * @returns {Object} new model config to use
     */
    _getNextConfig(currentConfig, params) {
        const config = Object.assign({}, currentConfig);
        config.context = { ...("context" in params ? params.context : config.context) };
        if ("domain" in params) {
            config.domain = params.domain;
            if (this.isSearchDefaultOrEmpty() && config.context.hierarchy_res_id) {
                config.domain = [["id", "=", config.context.hierarchy_res_id]];
                const globalDomain = this.globalDomain;
                if (globalDomain.length) {
                    config.domain = Domain.and([config.domain, globalDomain]).toList({});
                }
                // Just needed for the first load.
                delete config.context.hierarchy_res_id;
            }
        }
        config.orderBy = "orderBy" in params ? params.orderBy : config.orderBy;
        // re-apply previous orderBy if not given (or no order)
        if (!config.orderBy.length) {
            config.orderBy = currentConfig.orderBy || [];
        }
        // apply default order if no order
        if (this.defaultOrderBy && !config.orderBy.length) {
            config.orderBy = this.defaultOrderBy;
        }
        return config;
    }

    /**
     * Load data for hierarchy view
     *
     * @param {Object} config model config
     * @param {number[]} [resIds] ids to load instead of using the config domain
     * @returns {Promise<Object[]>}
     */
    async _loadData(config, resIds) {
        let onlyRoots = false;
        let domain = config.domain;
        if (resIds?.length) {
            domain = [["id", "in", resIds]];
        } else if (this.isSearchDefaultOrEmpty()) {
            // If the current SearchModel query is the default one configured for the action
            // or there is no search query, an additional constraint is added to only display
            // "root" records (without a parent).
            onlyRoots = true;
            domain = !domain.length
                ? this.defaultDomain
                : Domain.and([this.defaultDomain, domain]).toList({});
        }
        const hierarchyRead = (domain) =>
            this.orm.call(
                config.resModel,
                "hierarchy_read",
                [
                    domain,
                    this._getFieldsSpec(config.context),
                    this.parentFieldName,
                    this.childFieldName,
                    orderByToString(config.orderBy),
                ],
                { context: config.context }
            );
        let result = await hierarchyRead(domain);
        if (!result.length && onlyRoots) {
            result = await hierarchyRead(config.domain);
        }
        return result;
    }

    /**
     * @override
     * There is only one record per res id in the hierarchy, nothing to sync.
     */
    _updateSimilarRecords() {}
}
