/** @odoo-module native */
import { toRaw } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { _t } from "@web/core/translation";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { Model } from "@web/model/model";
import { getFieldsSpec } from "@web/model/relational_model";
import { orderByToString } from "@web/core/utils/order_by";

/**
 * @param {false | {id: Number, display_name?: String}} value
 * @returns {false | Number}
 */
function getIdOfMany2oneField(value) {
    return value ? value.id : false;
}

/**
 * @param {Object[]} records
 * @returns {Object[]}
 */
function uniqueById(records) {
    return [...new Map(records.map((record) => [record.id, record])).values()];
}

export class HierarchyNode {
    /**
     * @param {HierarchyModel} model
     * @param {Object} config
     * @param {Object} data
     * @param {HierarchyTree} tree
     * @param {HierarchyNode} parentNode
     * @param {Boolean} populateChildNodes
     */
    constructor(
        model,
        config,
        data,
        tree,
        parentNode = null,
        populateChildNodes = true,
    ) {
        this.id = model.nextNodeId();
        this.data = data;
        this.parentNode = parentNode;
        this.tree = tree;
        this.model = model;
        this._config = config;
        this.hidden = false;
        tree.addNode(this);
        if (populateChildNodes) {
            this.populateChildNodes();
        }
    }

    /**
     * Get ancestor node
     *
     * @returns {HierarchyNode} ancestor node
     */
    get ancestorNode() {
        return this.parentNode ? this.parentNode.ancestorNode : this;
    }

    /**
     * Is leaf?
     *
     * @returns {Boolean} False if the current node has node as child nodes, otherwise True.
     */
    get isLeaf() {
        return !this.nodes.length;
    }

    /** @returns {HierarchyForest} */
    get forest() {
        return this.tree.forest;
    }

    /** @returns {Number} */
    get resId() {
        return this.data.id;
    }

    /** @returns {String} */
    get parentFieldName() {
        return this.model.parentFieldName;
    }

    /** @returns {Number} */
    get parentResId() {
        return (
            this.parentNode?.resId ||
            getIdOfMany2oneField(this.data[this.parentFieldName])
        );
    }

    /** @returns {Number[]} */
    get childResIds() {
        return this._nodes.length
            ? this._nodes.map((node) => node.resId)
            : this.data[this.childFieldName]?.map((d) =>
                  typeof d === "number" ? d : d.id,
              ) || [];
    }

    /** @returns {String} */
    get childFieldName() {
        return this.model.childFieldName;
    }

    /** @returns {Boolean} */
    get hasChildren() {
        return this._nodes.length > 0 || this.data[this.childFieldName]?.length > 0;
    }

    /** @returns {Boolean} */
    get isOnlyOccurrenceOfItsRecord() {
        return this.forest.isResIdUnique(this.resId);
    }

    /** @returns {Boolean} */
    get canShowParentNode() {
        return (
            Boolean(this.parentResId) &&
            this.parentResId !== this.resId &&
            !this.parentNode &&
            this.isOnlyOccurrenceOfItsRecord
        );
    }

    /** @returns {Boolean} */
    get canShowChildNodes() {
        return (
            this.hasChildren &&
            this.nodes.length === 0 &&
            this.isOnlyOccurrenceOfItsRecord
        );
    }

    getDescendantNodes(hideNodesIncluded = false) {
        const subNodes = [];
        const nodes = hideNodesIncluded ? this._nodes : this.nodes;
        for (const node of nodes) {
            subNodes.push(node, ...node.getDescendantNodes(hideNodesIncluded));
        }
        return subNodes;
    }

    /** @returns {HierarchyNode[]} */
    get descendantsParentNodes() {
        if (this.isLeaf) {
            return [];
        }
        const parentNodes = [this];
        for (const node of this.nodes) {
            parentNodes.push(...node.descendantsParentNodes);
        }
        return parentNodes;
    }

    /** @returns {Number[]} */
    get allSubsidiaryResIds() {
        return this.getDescendantNodes().map((n) => n.resId);
    }

    get nodes() {
        return this._nodes.filter((n) => !n.hidden);
    }

    populateChildNodes() {
        this._nodes = [];
        const children = this.data[this.childFieldName] || [];
        if (
            children.length &&
            children[0] instanceof Object &&
            this.isOnlyOccurrenceOfItsRecord
        ) {
            this.createChildNodes(children);
        }
    }

    /** @param {Object[]} childNodesData */
    createChildNodes(childNodesData) {
        this._nodes = (childNodesData || this.data[this.childFieldName]).map(
            (childData) =>
                new HierarchyNode(this.model, this._config, childData, this.tree, this),
        );
    }

    removeParentNode() {
        this.parentNode?.removeChildNode(this);
        this.parentNode = null;
        this.data[this.parentFieldName] = false;
    }

    async fetchParentNode() {
        await this.model.fetchManager(this);
    }

    async showChildNodes() {
        if (!this.hasChildren) {
            return;
        }
        if (!this._nodes.length) {
            await this.model.fetchSubordinates(this);
            return;
        }
        this.model._searchNodeToCollapse(this)?.collapseChildNodes(true);
        for (const node of this.getDescendantNodes(true)) {
            node.hidden = false;
            this.tree.addNode(node);
        }
        this.model.notify();
    }

    /** @param hideNodes: */
    collapseChildNodes(hideNodes = false) {
        if (hideNodes) {
            const nodesToHide = this.getDescendantNodes();
            for (const node of nodesToHide) {
                node.hidden = true;
            }
            this.tree.removeNodes(nodesToHide);
        } else {
            const childrenData = [];
            for (const childNode of this.nodes) {
                childNode.data[this.childFieldName] = childNode.childResIds;
                childrenData.push(childNode.data);
            }
            this.data[this.childFieldName] = childrenData;
            this.removeChildNodes();
        }
        this.model.notify();
    }

    removeChildNode(node) {
        node.removeChildNodes();
        this.tree.removeNodes([node]);
        this._nodes = this._nodes.filter((n) => n.id !== node.id);
        this.data[this.childFieldName] = this._nodes.map((n) => n.data);
    }

    removeChildNodes(rootNode = this) {
        for (const childNode of this.nodes) {
            if (!childNode.isLeaf && childNode !== rootNode) {
                childNode.removeChildNodes(rootNode);
            }
        }
        this.tree.removeNodes(this._nodes);
        this._nodes = [];
    }

    /** @param {HierarchyNode} node */
    setParentNode(node) {
        const tree = node.tree;
        if (tree.root === this) {
            tree.root = node;
        } else if (this.tree.root === this) {
            this.tree.removeRoot();
            this.setTree(node.tree);
        }
        this.parentNode = node;
        node.addChildNode(this);
    }

    /** @param {HierarchyTree} tree */
    setTree(tree) {
        this.tree = tree;
        if (!this.hidden) {
            tree.addNode(this);
        }
        for (const childNode of this._nodes) {
            childNode.setTree(tree);
        }
    }

    /** @param {HierarchyNode} node */
    addChildNode(node) {
        this._nodes.push(node);
        this.data[this.childFieldName].push(node.data);
        this.tree.addNode(node);
    }
}

export class HierarchyTree {
    /**
     * @param {HierarchyModel} model
     * @param {Object} config
     * @param {Object} data
     * @param {HierarchyForest} forest
     */
    constructor(model, config, data, forest) {
        this.id = model.nextTreeId();
        this.model = model;
        this._config = config;
        this.forest = forest;
        this.nodePerNodeId = new Map();
        if (data) {
            this.root = new HierarchyNode(model, config, data, this);
        }
    }

    /** @returns {Number[]} */
    get resIds() {
        return [...this.nodePerNodeId.values()].map((node) => node.resId);
    }

    /** @param {HierarchyNode} node */
    addNode(node) {
        this.nodePerNodeId.set(node.id, node);
        this.forest.addNode(node);
    }

    /** @param {HierarchyNode[]} nodes */
    removeNodes(nodes) {
        for (const node of nodes) {
            this.nodePerNodeId.delete(node.id);
        }
        this.forest.removeNodes(nodes);
    }

    removeRoot() {
        this.forest.removeTree(this);
    }
}

export class HierarchyForest {
    /**
     * @param {HierarchyModel} model
     * @param {Object} config
     * @param {Object[]} data
     */
    constructor(model, config, data) {
        this.id = model.nextForestId();
        this.model = model;
        this._config = config;
        this.nodePerNodeId = new Map();
        this._nodeCountPerResId = new Map();
        this._trees = data.map((d) => new HierarchyTree(model, config, d, this));
    }

    get trees() {
        return this._trees.filter((t) => !t.root.hidden);
    }

    /** @returns {Number[]} */
    get resIds() {
        return [...this.nodePerNodeId.values()].map((node) => node.resId);
    }

    /** @returns {HierarchyNode[]} */
    get rootNodes() {
        return this.trees.map((t) => t.root);
    }

    /**
     * @param {Number} resId
     * @returns {Boolean}
     */
    isResIdUnique(resId) {
        return this._nodeCountPerResId.get(resId) === 1;
    }

    /** @param {HierarchyNode} node */
    addNode(node) {
        if (this.nodePerNodeId.has(node.id)) {
            return;
        }
        this.nodePerNodeId.set(node.id, node);
        this._nodeCountPerResId.set(
            node.resId,
            (this._nodeCountPerResId.get(node.resId) || 0) + 1,
        );
    }

    /** @param {HierarchyNode[]} nodes */
    removeNodes(nodes) {
        for (const node of nodes) {
            if (!this.nodePerNodeId.delete(node.id)) {
                continue;
            }
            const remaining = this._nodeCountPerResId.get(node.resId) - 1;
            if (remaining > 0) {
                this._nodeCountPerResId.set(node.resId, remaining);
            } else {
                this._nodeCountPerResId.delete(node.resId);
            }
        }
    }

    removeTree(tree) {
        this.removeNodes([...tree.nodePerNodeId.values()]);
        this._trees = this._trees.filter((t) => t.id !== tree.id);
    }
}

export class HierarchyModel extends Model {
    static services = ["notification"];

    setup(params, { notification }) {
        this.keepLast = new KeepLast();
        this.mutex = new Mutex();
        this.resModel = params.resModel;
        this.fields = params.fields;
        this.parentFieldName = params.parentFieldName;
        this.declaredChildFieldName = params.childFieldName;
        this.activeFields = params.activeFields;
        this.defaultOrderBy = params.defaultOrderBy;
        this.notification = notification;
        this._nodeId = 0;
        this._treeId = 0;
        this._forestId = 0;
        this.config = {
            domain: [],
            ...params.config,
            isRoot: true,
        };
    }

    nextNodeId() {
        return this._nodeId++;
    }

    nextTreeId() {
        return this._treeId++;
    }

    nextForestId() {
        return this._forestId++;
    }

    /** @returns {Object} */
    get parentField() {
        return this.fields[this.parentFieldName];
    }

    /** @returns {Number[]} */
    get resIds() {
        return this.root?.resIds || [];
    }

    /**
     * @override
     * @returns {Boolean}
     */
    hasData() {
        return this.resIds.length > 0;
    }

    /** @returns {String} */
    get defaultChildFieldName() {
        return "__child_ids__";
    }

    /** @returns {String} */
    get childFieldName() {
        return this.declaredChildFieldName || this.defaultChildFieldName;
    }

    /** @returns {import("@web/core/domain").DomainListRepr} */
    get globalDomain() {
        if (!this.env.searchModel?.globalDomain.length) {
            return [];
        }
        return new Domain(this.env.searchModel.globalDomain).toList(
            this.env.searchModel.domainEvalContext,
        );
    }

    /** @returns {String[]} */
    get activeFieldNames() {
        return Object.keys(this.activeFields);
    }

    get context() {
        return {
            bin_size: true,
            ...(this.config.context || {}),
        };
    }

    exportState() {
        return {
            config: toRaw({
                ...this.config,
                resIds: this.resIds,
            }),
        };
    }

    /** @param {Object} params */
    async load(params = {}) {
        const { resIds, ...config } = this._getNextConfig(this.config, params);
        const data = await this.keepLast.add(this._loadData({ ...config, resIds }));
        this.root = this._createRoot(config, data);
        this.config = config;
        this.notify({ scrollTarget: "none" });
    }

    async reload() {
        const data = await this.keepLast.add(this._loadData(this.config, true));
        this.root = this._createRoot(this.config, data);
        this.notify({ scrollTarget: "none" });
    }

    /** @override */
    notify(payload = { scrollTarget: "bottom" }) {
        super.notify();
        this.bus.trigger("hierarchyScrollTarget", payload);
    }

    /** @param {HierarchyNode} node */
    async fetchManager(node) {
        if (this.root.trees.length > 1) {
            const treeExpanded = this._findTreeExpanded();
            const resIdsToFetch = [
                node.parentResId,
                node.resId,
                ...node.allSubsidiaryResIds,
            ];
            if (
                treeExpanded &&
                treeExpanded.root.id !== node.id &&
                treeExpanded.root.parentResId === node.parentResId
            ) {
                resIdsToFetch.push(...treeExpanded.root.allSubsidiaryResIds);
            }
            const config = {
                ...this.config,
                domain: [
                    "|",
                    [this.parentFieldName, "=", node.parentResId],
                    ["id", "in", resIdsToFetch],
                ],
            };
            const data = await this._loadData(config);
            this.root = this._createRoot(config, data);
            this.notify();
            return;
        }
        const managerData = await this.keepLast.add(this._fetchManager(node));
        if (!managerData) {
            this.notification.add(_t("The parent record is no longer available."), {
                type: "warning",
            });
            return;
        }
        const parentNode = new HierarchyNode(
            this,
            this.config,
            managerData,
            node.tree,
            null,
            false,
        );
        parentNode.createChildNodes();
        node.setParentNode(parentNode);
        this.notify({ scrollTarget: "up" });
    }

    /** @param {HierarchyNode} node */
    async fetchSubordinates(node) {
        const childFieldName = this.childFieldName;
        const children = node.data[childFieldName];
        if (!children?.length) {
            return;
        }
        const nodesToUpdate = [];
        if (!(children[0] instanceof Object)) {
            const allNodeResIds = this.root.resIds;
            let existingChildResIds = children.filter((childResId) =>
                allNodeResIds.includes(childResId),
            );
            if (existingChildResIds.length) {
                for (const tree of this.root.trees) {
                    if (
                        existingChildResIds.includes(tree.root.resId) &&
                        tree.root.id !== node.id
                    ) {
                        if (node.tree.id === tree.id) {
                            existingChildResIds = existingChildResIds.filter(
                                (resId) => resId !== tree.root.resId,
                            );
                            continue;
                        }
                        nodesToUpdate.push(tree.root);
                    }
                }
            }
            const subordinates = await this.keepLast.add(
                this._fetchSubordinates(node, existingChildResIds),
            );
            if (subordinates.length) {
                node.data[childFieldName] = subordinates;
            }
        }
        const nodeToCollapse = this._searchNodeToCollapse(node);
        if (nodeToCollapse && !nodesToUpdate.includes(nodeToCollapse)) {
            nodeToCollapse.collapseChildNodes(true);
        }
        node.populateChildNodes();
        for (const n of nodesToUpdate) {
            n.setParentNode(node);
        }
        this.notify();
    }

    /**
     * @param {HierarchyNode} node
     * @returns {HierarchyNode | null}
     */
    _searchNodeToCollapse(node) {
        const parentNode = node.parentNode;
        if (parentNode) {
            return parentNode.nodes.find((n) => n.nodes.length) || null;
        }
        return this._findTreeExpanded()?.root || null;
    }

    _findTreeExpanded() {
        return this.root.trees.find((t) => t.root.nodes.length);
    }

    /**
     * @param {Object} currentConfig
     * @param {Object} params
     * @returns {Object}
     */
    _getNextConfig(currentConfig, params) {
        const config = Object.assign({}, currentConfig);
        config.context = "context" in params ? params.context : config.context;
        if ("domain" in params) {
            config.domain = params.domain;
            if (this.isSearchDefaultOrEmpty() && config.context?.hierarchy_res_id) {
                config.domain = [["id", "=", config.context.hierarchy_res_id]];
                const globalDomain = this.globalDomain;
                if (globalDomain.length) {
                    config.domain = Domain.and([config.domain, globalDomain]);
                }
                delete config.context.hierarchy_res_id;
            }
        }

        config.orderBy = "orderBy" in params ? params.orderBy : config.orderBy;
        if (!config.orderBy.length) {
            config.orderBy = currentConfig.orderBy || [];
        }
        if (this.defaultOrderBy && !config.orderBy.length) {
            config.orderBy = this.defaultOrderBy;
        }
        return config;
    }

    _getFieldsSpec(context = this.config.context) {
        return getFieldsSpec(this.activeFields, this.fields, context);
    }

    /** @returns {boolean} */
    isSearchDefaultOrEmpty() {
        if (!this.env.searchModel) {
            return true;
        }
        const isDisabledOptionalSearchMenuType = (type) => {
            return (
                ["filter", "groupBy", "favorite"].includes(type) &&
                !this.env.searchModel.searchMenuTypes.has(type)
            );
        };
        const activeSearchItems = this.env.searchModel.getSearchItems(
            (item) => item.isActive && !isDisabledOptionalSearchMenuType(item.type),
        );
        if (!activeSearchItems.length) {
            return true;
        }
        const defaultSearchItems = this.env.searchModel.getSearchItems(
            (item) =>
                item.isDefault &&
                item.type !== "favorite" &&
                !isDisabledOptionalSearchMenuType(item.type),
        );
        return (
            defaultSearchItems.length === activeSearchItems.length &&
            defaultSearchItems.every(
                (item, index) => item.id === activeSearchItems[index].id,
            )
        );
    }

    /**
     * @param {Object} config
     * @param {boolean} reload
     * @returns {Object[]}
     */
    async _loadData(config, reload = false) {
        const resIds = reload ? this.resIds : config.resIds;
        if (resIds?.length > 0) {
            return this._formatData(
                await this._hierarchyRead([["id", "in", resIds]], config, false),
            );
        }
        const onlyRoots = this.isSearchDefaultOrEmpty();
        return this._formatData(
            await this._hierarchyRead(config.domain, config, onlyRoots),
        );
    }

    /**
     * @param {import("@web/core/domain").DomainListRepr} domain
     * @param {Object} config
     * @param {Boolean} onlyRoots
     * @returns {Promise<Object[]>}
     */
    _hierarchyRead(domain, config, onlyRoots) {
        return this.orm.call(
            this.resModel,
            "hierarchy_read",
            [
                domain,
                this._getFieldsSpec(config.context),
                this.parentFieldName,
                this.declaredChildFieldName,
                orderByToString(config.orderBy),
                onlyRoots,
            ],
            { context: this.context },
        );
    }

    /**
     * @param {Object[]} data
     * @returns {Object[]}
     */
    _formatData(data) {
        const childFieldName = this.childFieldName;
        const recordPerId = new Map();
        const recordsPerParentId = {};
        for (const record of data) {
            recordPerId.set(record.id, record);
            const parentId = getIdOfMany2oneField(record[this.parentFieldName]);
            recordsPerParentId[parentId] ||= [];
            recordsPerParentId[parentId].push(record);
        }
        const rootRecords = [];
        const branches = [];
        const siblingIdsOfCollectedParents = new Set();
        for (const [parentId, records] of Object.entries(recordsPerParentId)) {
            const parentRecord = recordPerId.get(Number(parentId));
            if (!parentRecord) {
                rootRecords.push(...uniqueById(records));
                continue;
            }
            if (siblingIdsOfCollectedParents.has(parentRecord.id)) {
                return data;
            }
            const ancestorId = getIdOfMany2oneField(parentRecord[this.parentFieldName]);
            for (const sibling of recordsPerParentId[ancestorId] || []) {
                siblingIdsOfCollectedParents.add(sibling.id);
            }
            branches.push([parentRecord, uniqueById(records)]);
        }
        for (const [parentRecord, children] of branches) {
            parentRecord[childFieldName] = children;
        }
        if (!rootRecords.length && branches.length) {
            rootRecords.push(branches[0][0]);
        }
        return rootRecords;
    }

    /**
     * @param {Object} config
     * @param {Object[]} data
     * @returns {HierarchyForest}
     */
    _createRoot(config, data) {
        return new HierarchyForest(this, config, data);
    }

    /**
     * @param {HierarchyNode} node
     * @returns {Object}
     */
    async _fetchManager(node) {
        const domain = Domain.and([
            [
                "|",
                ["id", "=", node.parentResId],
                [this.parentFieldName, "=", node.parentResId],
            ],
            [["id", "!=", node.resId]],
        ]);
        const { records = [] } = await this.orm.webSearchRead(
            this.resModel,
            domain.toList({}),
            {
                context: this.context,
                specification: this._getFieldsSpec(),
                order: orderByToString(this.config.orderBy),
            },
        );
        const managerData = records.find((data) => data.id === node.parentResId);
        if (!managerData) {
            return null;
        }
        const children = records.filter((data) => data.id !== node.parentResId);
        if (!this.declaredChildFieldName && children.length) {
            await this._fetchDescendants(children);
        }
        managerData[this.childFieldName] = children;
        return managerData;
    }

    /**
     * @param {HierarchyNode} node
     * @param {Array<number> | null} excludeResIds
     * @returns {Object[]}
     */
    async _fetchSubordinates(node, excludeResIds = null) {
        let childrenResIds = node.data[this.childFieldName];
        if (excludeResIds) {
            childrenResIds = childrenResIds.filter(
                (childResId) => !excludeResIds.includes(childResId),
            );
        }
        if (!childrenResIds.length) {
            return [];
        }
        const { records } = await this.orm.webSearchRead(
            this.resModel,
            [["id", "in", childrenResIds]],
            {
                specification: this._getFieldsSpec(),
                context: this.context,
                order: orderByToString(this.config.orderBy),
            },
        );
        if (!this.declaredChildFieldName) {
            await this._fetchDescendants(records);
        }
        return records;
    }

    /** @param {Object[]} childrenData */
    async _fetchDescendants(childrenData) {
        const resIds = childrenData.map((d) => d.id);
        if (!resIds.length) {
            return;
        }
        const fetchChildren = await this.orm.formattedReadGroup(
            this.resModel,
            [[this.parentFieldName, "in", resIds]],
            [this.parentFieldName],
            ["id:array_agg"],
            { context: this.context },
        );
        const childIdsPerId = new Map(
            fetchChildren.map((g) => [g[this.parentFieldName][0], g["id:array_agg"]]),
        );
        for (const d of childrenData) {
            if (childIdsPerId.has(d.id)) {
                d[this.childFieldName] = childIdsPerId.get(d.id);
            }
        }
    }

    /**
     * @param {HierarchyNode} node
     * @param {Number} parentResId
     */
    async updateParentId(node, parentResId = false) {
        return this.orm.write(
            this.resModel,
            [node.resId],
            { [this.parentFieldName]: parentResId },
            { context: this.context },
        );
    }

    /**
     * @param {Number} nodeId
     * @param {Object} parentInfo
     * @param {Number} [parentInfo.parentNodeId]
     * @param {Number | false} [parentInfo.parentResId]
     * @returns {Promise}
     */
    async updateParentNode(nodeId, { parentNodeId, parentResId }) {
        const node = this.root.nodePerNodeId.get(nodeId);
        if (!node) {
            return;
        }
        const resId = node.resId;
        const parentNode =
            parentNodeId === undefined
                ? null
                : this.root.nodePerNodeId.get(parentNodeId) || null;
        parentResId = parentResId || parentNode?.resId || false;
        const oldParentNode = node.parentNode;
        if (
            (parentNode && !this.validateUpdateParentNode(node, parentNode)) ||
            parentNode?.resId === oldParentNode?.resId
        ) {
            return;
        }
        node.hidden = true;
        this.notify({ scrollTarget: "none" });
        await this.mutex.exec(async () => {
            try {
                await this.updateParentId(node, parentResId);
            } catch (error) {
                node.hidden = false;
                this.notify({ scrollTarget: "none" });
                throw error;
            }
        });
        const domain = this.computeUpdateParentNodeDomain(
            node,
            parentResId,
            parentNode,
        );
        const data = await this.orm.webSearchRead(this.resModel, domain, {
            specification: this._getFieldsSpec(),
            context: this.context,
            order: orderByToString(this.config.orderBy),
        });
        if (!data.length) {
            return this.reload();
        }
        const formattedData = this._formatData(data.records);
        for (const record of formattedData) {
            if (getIdOfMany2oneField(record[this.parentFieldName]) !== parentResId) {
                node.hidden = false;
                this.notify({ scrollTarget: "none" });
                this.notification.add(
                    _t(
                        `The parent of "%s" was successfully updated. Reloading records to account for other changes.`,
                        node.data.display_name || node.data.name,
                    ),
                    { type: "success" },
                );
                return this.reload();
            }
        }
        const nodeToCollapse = this._searchNodeToCollapseAfterMove(node, parentNode);
        if (oldParentNode) {
            oldParentNode.removeChildNode(node);
        } else {
            node.tree.removeRoot();
        }
        nodeToCollapse?.collapseChildNodes();
        if (!parentNode) {
            this.root = this._createRoot(this.config, formattedData);
        } else {
            parentNode.data[this.childFieldName] = formattedData;
            parentNode.populateChildNodes();
        }
        const newNode = [...this.root.nodePerNodeId.values()].find(
            (n) => n.resId === resId,
        );
        this.notify({ scrollTarget: newNode?.id });
    }

    /**
     * @param {HierarchyNode} node
     * @param {HierarchyNode} [parentNode]
     * @returns {HierarchyNode | undefined}
     */
    _searchNodeToCollapseAfterMove(node, parentNode) {
        const treeExpanded = this._findTreeExpanded();
        const expandedParentNodeIds =
            treeExpanded?.root.descendantsParentNodes.map((n) => n.id) || [];
        if (node.isLeaf && expandedParentNodeIds.includes(parentNode?.id)) {
            return parentNode;
        }
        const depth = expandedParentNodeIds.indexOf(parentNode?.parentNode?.id);
        if (depth === -1) {
            return treeExpanded?.root;
        }
        const nodeIdToCollapse = expandedParentNodeIds.at(depth + 1);
        return nodeIdToCollapse === undefined
            ? undefined
            : treeExpanded?.nodePerNodeId.get(nodeIdToCollapse);
    }

    validateUpdateParentNode(node, parentNode) {
        if (parentNode.resId === node.resId) {
            this.notification.add(
                _t("The parent record cannot be the record dragged."),
                {
                    type: "danger",
                },
            );
            return false;
        } else if (node.allSubsidiaryResIds.includes(parentNode.resId)) {
            this.notification.add(
                _t("Cannot change the parent because it would create a cycle."),
                {
                    type: "danger",
                },
            );
            return false;
        }
        return true;
    }

    /**
     * @param {HierarchyNode} node
     * @param {Number | false} parentResId
     * @param {HierarchyNode} [parentNode]
     * @returns {Array}
     */
    computeUpdateParentNodeDomain(node, parentResId, parentNode) {
        const domainsOr = [[["id", "=", node.resId]]];
        domainsOr.push([[this.parentFieldName, "=", parentResId]]);
        let expandedTreeRoot = null;
        if (!node.isLeaf) {
            expandedTreeRoot = node;
        } else if (!parentNode) {
            expandedTreeRoot = node.tree.root;
        } else if (!parentNode.isLeaf) {
            expandedTreeRoot = parentNode;
        }
        if (expandedTreeRoot) {
            const expandedTreeParentResIds =
                expandedTreeRoot.descendantsParentNodes.map((n) => n.resId);
            domainsOr.push([[this.parentFieldName, "in", expandedTreeParentResIds]]);
        }
        let domain = Domain.or(domainsOr);
        if (this.config.domain?.length) {
            domain = Domain.and([domain, this.config.domain]);
        }
        return domain.toList({});
    }
}
