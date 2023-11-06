/** @odoo-module */

import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { KeepLast, Mutex } from "@web/core/utils/concurrency";
import { pick } from "@web/core/utils/objects";
import { Model } from "@web/model/model";

let nodeId = 0;
let forestId = 0;
let treeId = 0;

/**
 * Get the id of the given many2one field value
 *
 * @param {false | [Number, string]} value many2one value
 * @returns {false | Number} id of the many2one
 */
function getIdOfMany2oneField(value) {
    return value && value[0];
}

export class HierarchyNode {
    /**
     * Constructor of hierarchy node stored in hierarchy tree
     *
     * @param {HierarchyModel} model
     * @param {Object} config
     * @param {Object} data
     * @param {HierarchyTree} tree
     * @param {HierarchyNode} parentNode
     * @param {Boolean} populateChildNodes
     */
    constructor(model, config, data, tree, parentNode = null, populateChildNodes = true) {
        this.id = nodeId++;
        this.data = data;
        this.parentNode = parentNode;
        this.tree = tree;
        this.model = model;
        this._config = config;
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
        return this.parentNode ? this.ancestorNode : this;
    }

    /**
     * Is leaf?
     *
     * @returns {Boolean} False if the current node has node as child nodes, otherwise True.
     */
    get isLeaf() {
        return !this.nodes.length;
    }

    /**
     * Get forest of the current node
     *
     * @returns {HierarchyForest}
     */
    get forest() {
        return this.tree.forest;
    }

    /**
     * Get the resId of current node
     *
     * @returns {Number}
     */
    get resId() {
        return this.data.id;
    }

    /**
     * Get parent field name
     *
     * @returns {String}
     */
    get parentFieldName() {
        return this.model.parentFieldName;
    }

    /**
     * Get parent res id
     *
     * @returns {Number}
     */
    get parentResId() {
        return this.parentNode?.resId || getIdOfMany2oneField(this.data[this.parentFieldName]);
    }

    /**
     * Get child node res ids
     *
     * @returns {Number[]}
     */
    get childResIds() {
        return this.nodes.length ? this.nodes.map((node) => node.resId) : this.data[this.childFieldName]?.map((d) => typeof d === "number" ? d : d.id) || [];
    }

    /**
     * Get child field name
     *
     * @returns {String}
     */
    get childFieldName() {
        return this.model.childFieldName || this.model.defaultChildFieldName;
    }

    /**
     * Has child nodes?
     *
     * @returns {Boolean}
     */
    get hasChildren() {
        return this.nodes.length > 0 || this.data[this.childFieldName]?.length > 0;
    }

    /**
     * Can show parent node
     *
     * Knows if the parent node can be fetched and displayed inside the view
     *
     * @returns {Boolean} True if the current node has a parent node but it is not yet displayed and the data of the
     *                    current node is not already displayed in another node.
     */
    get canShowParentNode() {
        return Boolean(this.parentResId)
            && !this.parentNode
            && this.tree.forest.resIds.filter((resId) => resId === this.resId).length === 1;
    }


    /**
     * Can show child nodes
     *
     * Knows if the child nodes can be fetched and displayed inside the view
     *
     * @returns {Boolean} True if the current node has child nodes but they are not yet displayed and the data of the
     *                    current node is not already displayed in another node.
     */
    get canShowChildNodes() {
        return this.hasChildren
            && this.nodes.length === 0
            && this.tree.forest.resIds.filter((resId) => resId === this.resId).length === 1;
    }

    get descendantNodes() {
        const subNodes = [];
        if (!this.isLeaf) {
            subNodes.push(...this.nodes);
            for (const node of this.nodes) {
                if (node.descendantNodes.length) {
                    subNodes.push(...node.descendantNodes);
                }
            }
        }
        return subNodes;
    }

    /**
     * Get all descendants nodes resIds
     *
     * @returns {Number[]}
     */
    get allSubsidiaryResIds() {
        return this.descendantNodes.map((n) => n.resId);
    }

    /**
     * Populate child nodes
     *
     * Uses to create child nodes of the current one according to its data.
     */
    populateChildNodes() {
        this.nodes = [];
        const children = this.data[this.childFieldName] || [];
        if (
            children.length
            && children[0] instanceof Object
            && this.tree.forest.resIds.filter((resId) => resId === this.resId).length === 1
        ) {
            this.createChildNodes(children);
        }
    }

    /**
     * create child nodes
     *
     * @param {Object[]} childNodesData data of child nodes to generate
     */
    createChildNodes(childNodesData) {
        this.nodes = (childNodesData || this.data[this.childFieldName]).map(
            (childData) =>
                new HierarchyNode(
                    this.model,
                    this._config,
                    childData,
                    this.tree,
                    this
                )
        );
    }

    removeParentNode() {
        this.parentNode?.removeChildNode(this);
        this.parentNode = null;
        this.data[this.parentFieldName] = false;
    }

    /**
     * Fetch parent node
     */
    async fetchParentNode() {
        await this.model.fetchManager(this);
    }

    /**
     * Fetch child nodes
     */
    async showChildNodes() {
        await this.model.fetchSubordinates(this);
    }

    /**
     * Collapse child nodes
     *
     * Removes the descendant nodes of the current one and stores
     * the resIds of the child nodes in the data of the current one
     * to know it has child nodes to be able to show them again
     * when it is needed.
     */
    collapseChildNodes() {
        const childrenData = [];
        for (const childNode of this.nodes) {
            childNode.data[this.childFieldName] = childNode.childResIds;
            childrenData.push(childNode.data);
        }
        this.data[this.childFieldName] = childrenData;
        this.removeChildNodes();
        this.model.notify();
    }

    removeChildNode(node) {
        this.tree.removeNodes([node, ...node.descendantNodes]);
        this.nodes = this.nodes.filter((n) => n.id !== node.id);
        this.data[this.childFieldName] = this.nodes.map((n) => n.data);
    }

    /**
     * Remove descendant nodes of the current one
     */
    removeChildNodes() {
        for (const childNode of this.nodes) {
            if (!childNode.isLeaf) {
                childNode.removeChildNodes();
            }
        }
        this.tree.removeNodes(this.nodes);
        this.nodes = [];
    }

    /**
     * Set parent node to the current node
     *
     * @param {HierarchyNode} node parent node to set
     */
    setParentNode(node) {
        this.parentNode = node;
        node.addChildNode(this);
        const tree = node.tree;
        if (tree.root === this) {
            tree.root = node;
        } else if (this.tree.root === this) {
            this.tree.removeRoot();
            this.setTree(node.tree);
        }
    }

    setTree(tree) {
        this.tree = tree;
        for (const childNode of this.nodes) {
            childNode.setTree(tree);
        }
    }

    /**
     * Adds child node to the current node
     *
     * @param {HierarchyNode} node child node to add
     */
    addChildNode(node) {
        this.nodes.push(node);
        this.data[this.childFieldName].push(node.data);
        this.tree.addNode(node);
    }
}

export class HierarchyTree {
    /**
     * Constructor
     *
     * @param {HierarchyModel} model
     * @param {Object} config config of the model
     * @param {Object} data root node data of the tree to create
     * @param {HierarchyForest} forest hierarchy forest containing the tree to create
     */
    constructor(model, config, data, forest) {
        this.id = treeId++;
        this.nodePerNodeId = {};
        this.forest = forest;
        if (data) {
            this.root = new HierarchyNode(model, config, data, this);
            this.forest.nodePerNodeId = {
                ...this.forest.nodePerNodeId,
                ...this.nodePerNodeId,
            };
        }
        this.model = model;
        this._config = config;
    }

    /**
     * Get node res ids inside the current tree
     *
     * @returns {Number}
     */
    get resIds() {
        return Object.values(this.nodePerNodeId).map((node) => node.resId);
    }

    /**
     * Add node inside the current tree
     *
     * @param {HierarchyNode} node node to add inside the current tree
     */
    addNode(node) {
        this.nodePerNodeId[node.id] = node;
        this.forest.addNode(node);
    }

    /**
     * Remove nodes inside the current tree
     *
     * @param {HierarchyNode} nodes nodes to remove
     */
    removeNodes(nodes) {
        const nodeIds = nodes.map((node) => node.id);
        this.nodePerNodeId = Object.fromEntries(
            Object.entries(this.nodePerNodeId)
                .filter(
                    ([nodeId,]) => !nodeIds.includes(Number(nodeId))
                )
            );
        this.forest.removeNodes(nodes);
    }

    removeRoot() {
        this.forest.removeTree(this);
    }
}

export class HierarchyForest {
    /**
     *
     * @param {HierarchyModel} model
     * @param {Object} config model config
     * @param {Object[]} data list of tree root nodes data
     */
    constructor(model, config, data) {
        this.id = forestId++;
        this.nodePerNodeId = {};
        this.trees = data.map((d) => new HierarchyTree(model, config, d, this));
        this.model = model;
        this._config = config;
    }

    /**
     * Get node res ids containing inside the current forest
     *
     * @returns {Number}
     */
    get resIds() {
        return Object.values(this.nodePerNodeId).map((node) => node.resId);
    }

    /**
     * Get root node of all trees inside the current forest
     *
     * @returns {HierarchyNode[]} root nodes
     */
    get rootNodes() {
        return this.trees.map((t) => t.root);
    }

    /**
     * Add a node inside the current forest
     *
     * @param {HierarchyNode} node node to add inside the current forest
     */
    addNode(node) {
        this.nodePerNodeId[node.id] = node;
    }

    /**
     * Removes nodes inside the current forest
     *
     * @param {HierarchyNode} nodes nodes to remove inside the current forest
     */
    removeNodes(nodes) {
        const nodeIds = nodes.map((node) => node.id);
        this.nodePerNodeId = Object.fromEntries(
            Object.entries(this.nodePerNodeId)
                .filter(
                    ([nodeId,]) => !nodeIds.includes(Number(nodeId))
                )
        );
    }

    addNewRootNode(node) {
        const tree = new HierarchyTree(this.model, this._config, null, this);
        tree.root = node;
        node.tree = tree;
        tree.addNode(node);
        for (const subNode of node.descendantNodes) {
            tree.addNode(subNode);
        }
        this.trees.push(tree);
    }

    removeTree(tree) {
        this.nodePerNodeId = Object.fromEntries(
            Object.entries(this.nodePerNodeId)
                .filter(
                    ([nodeId, ]) => !(nodeId in tree.nodePerNodeId)
                )
        );
        this.trees = this.trees.filter((t) => t.id !== tree.id);
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
        this.childFieldName = params.childFieldName;
        this.activeFields = params.activeFields;
        this.notification = notification;
        this.config = {
            domain: this.defaultDomain,
            isRoot: true,
        };
    }

    /**
     * Get parent field info
     *
     * @returns {Object} parent field info
     */
    get parentField() {
        return this.fields[this.parentFieldName];
    }

    /**
     * Get res ids of all nodes displayed in the view
     *
     * @returns {Number[]} resIds of all nodes displayed in the view
     */
    get resIds() {
        return this.root?.resIds || [];
    }

    /**
     * Get default child field name when no child field name is given to the view
     *
     * @returns {String} default child field name to use
     */
    get defaultChildFieldName() {
        return "__child_ids__";
    }

    /**
     * Get active fields name
     *
     * @returns {String[]} active fields name
     */
    get activeFieldNames() {
        return Object.keys(this.activeFields);
    }

    /**
     * Get default domain to use, when no domain is given in the config
     *
     * @returns {import("@web/src/core/domain").DomainListRepr} default domain
     */
    get defaultDomain() {
        return [[this.parentFieldName, '=', false]];
    }

    /**
     * Get fields to fetch
     * @returns {String[]} fields to fetch
     */
    get fieldsToFetch() {
        const fieldsToFetch = [
            ...this.activeFieldNames,
        ];
        if (this.childFieldName) {
            fieldsToFetch.push(this.childFieldName);
        }
        return fieldsToFetch;
    }

    /**
     * Load the config and data for hierarchy view
     *
     * @param {Object} params params to use to load data of hierarchy view
     */
    async load(params = {}) {
        nodeId = forestId = treeId = 0;
        const config = this._getNextConfig(this.config, params);
        const data = await this.keepLast.add(this._loadData(config));
        this.root = this._createRoot(config, data);
        this.config = config;
        this.notify();
    }

    /**
     * Fetch parent node of given node
     * @param {HierarchyNode} node node to fetch its parent node
     */
    async fetchManager(node) {
        if (this.root.trees.length > 1) { // reset the hierarchy
            const treeExpanded = this._findTreeExpanded();
            const resIdsToFetch = [node.parentResId, node.resId, ...node.allSubsidiaryResIds];
            if (treeExpanded && treeExpanded.root.id !== node.id && treeExpanded.root.parentResId === node.parentResId) {
                resIdsToFetch.push(...treeExpanded.root.allSubsidiaryResIds);
            }
            const config = {
                ...this.config,
                domain: ["|", [this.parentFieldName, "=", node.parentResId], ["id", "in", resIdsToFetch]],
            }
            const data = await this._loadData(config);
            this.root = this._createRoot(config, data);
            this.notify();
            return;
        }
        const managerData = await this.keepLast.add(this._fetchManager(node));
        if (managerData) {
            const parentNode = new HierarchyNode(this, this.config, managerData, node.tree, null, false);
            parentNode.createChildNodes();
            node.setParentNode(parentNode);
            this.notify();
        }
    }

    /**
     * Fetch child nodes of given node
     *
     * @param {HierarchyNode} node node to fetch its child nodes
     */
    async fetchSubordinates(node) {
        const childFieldName = this.childFieldName || this.defaultChildFieldName;
        const children = node.data[childFieldName];
        if (children.length) {
            const nodesToUpdate = [];
            if (!(children[0] instanceof Object)) {
                const allNodeResIds = this.root.resIds;
                const existingChildResIds = children.filter((childResId) => allNodeResIds.includes(childResId))
                if (existingChildResIds.length) { // special case with result found with the search view
                    for (const tree of this.root.trees) {
                        if (existingChildResIds.includes(tree.root.resId)) {
                            nodesToUpdate.push(tree.root);
                        }
                    }
                }
                const data = await this.keepLast.add(this._fetchSubordinates(node, existingChildResIds));
                if (data && data.length) {
                    node.data[childFieldName] = data;
                }
            }
            const nodeToCollapse = this._searchNodeToCollapse(node);
            if (nodeToCollapse && !nodesToUpdate.includes(nodeToCollapse)) {
                nodeToCollapse.collapseChildNodes();
            }
            node.populateChildNodes();
            for (const n of nodesToUpdate) {
                n.setParentNode(node);
            }
            this.notify();
        }
    }

    /**
     * Search node to collapse to be able to show the child nodes of node given in parameter
     *
     * @param {HierarchyNode} node node to show its child nodes.
     * @returns {HierarchyNode | null} node found to collapse
     */
    _searchNodeToCollapse(node) {
        const parentNode = node.parentNode;
        let nodeToCollapse = null;
        if (parentNode) {
            nodeToCollapse = parentNode.nodes.find((n) => n.nodes.length);
        } else {
            const treeExpanded = this._findTreeExpanded();
            if (treeExpanded) {
                nodeToCollapse = treeExpanded.root;
            }
        }
        return nodeToCollapse;
    }

    _findTreeExpanded() {
        return this.root.trees.find((t) => t.root.nodes.length);
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
        config.context = "context" in params ? params.context : config.context;
        if ("domain" in params) {
            config.domain = params.domain;
            if (!params.domain.length) {
                if (config.context.hierarchy_res_id) {
                    config.domain = [["id", "=", config.context.hierarchy_res_id]];
                    delete config.context.hierarchy_res_id; // just needed for the first load.
                } else {
                    config.domain = this.defaultDomain;
                }
            }
        }
        return config;
    }

    /**
     * Load data for hierarchy view
     *
     * @param {Object} config model config
     * @returns {Object[]} main data for hierarchy view
     */
    async _loadData(config) {
        const result = await this.orm.call(
            this.resModel,
            "hierarchy_read",
            [config.domain, this.fieldsToFetch, this.parentFieldName, this.childFieldName],
            {
                context: config.context,
            },
        );
        const resultStringified = JSON.stringify(result);
        const recordsPerParentId = {};
        const recordPerId = {};
        for (const record of result) {
            recordPerId[record.id] = record;
            const parentId = getIdOfMany2oneField(record[this.parentFieldName]);
            if (!(parentId.toString() in recordsPerParentId)) {
                recordsPerParentId[parentId] = [];
            }
            recordsPerParentId[parentId].push(record);
        }
        const data = [];
        const recordIds = []; // to check if we have only one arborescence to display otherwise we display the result as the kanban view
        for (const [parentId, records] of Object.entries(recordsPerParentId)) {
            if (!parentId || !(parentId in recordPerId)) {
                data.push(...records);
            } else {
                const parentRecord = recordPerId[parentId];
                if (recordIds.includes(parentRecord.id)) {
                    return JSON.parse(resultStringified);
                }
                const ancestorId = getIdOfMany2oneField(parentRecord[this.parentFieldName]);
                if (ancestorId in recordsPerParentId) {
                    recordIds.push(...recordsPerParentId[ancestorId].map((r) => r.id));
                }
                parentRecord[this.childFieldName || this.defaultChildFieldName] = records;
            }
        }
        if (!data.length && result?.length) {
            data.push(recordPerId[Object.keys(recordsPerParentId)[0]]);
        }
        return data;
    }

    /**
     * Create forest
     *
     * @param {Object} config model config to use
     * @param {Object[]} data root data
     * @returns {HierarchyForest} forest hierarchy
     */
    _createRoot(config, data) {
        return new HierarchyForest(this, config, data);
    }

    /**
     * Fetch parent node and its children nodes data
     *
     * @param {HierarchyNode} node node to fetch its parent node
     * @returns {Object} the parent node data with children data inside childFieldName
     */
    async _fetchManager(node, exclude_node=true) {
        let domain = new Domain([
            "|",
                ["id", "=", node.parentResId],
                [this.parentFieldName, "=", node.parentResId],
        ]);
        if (exclude_node) {
            domain = Domain.and([
                domain,
                [["id", "!=", node.resId]],
            ])
        }
        const result = await this.orm.searchRead(
            this.resModel,
            domain.toList({}),
            this.fieldsToFetch,
            { context: this.config.context },
        );
        let managerData = {};
        const children = [];
        for (const data of result) {
            if (data.id === node.parentResId) {
                managerData = data;
            } else {
                children.push(data);
            }
        }
        if (!this.childFieldName) {
            if (children.length) {
                await this._fetchDescendants(children);
            }
        }
        managerData[this.childFieldName || this.defaultChildFieldName] = children;
        return managerData;
    }

    /**
     * Fetch children nodes data for a given node
     *
     * @param {HierarchyNode} node node to fetch its children nodes
     * @param {Array<number> | null} excludeResIds list of ids to exclude (because the nodes already exist)
     * @returns {Object[]} list of child node data
     */
    async _fetchSubordinates(node, excludeResIds = null) {
        let childrenResIds = node.data[this.childFieldName || this.defaultChildFieldName];
        if (excludeResIds) {
            childrenResIds = childrenResIds.filter((childResId) => !excludeResIds.includes(childResId));
        }
        const data = await this.orm.read(
            this.resModel,
            childrenResIds,
            this.fieldsToFetch,
            { context: this.config.context },
        )
        if (!this.childFieldName) {
            await this._fetchDescendants(data);
        }
        return data;
    }

    /**
     * fetch descendants nodes resIds to know if the child nodes have descendants
     *
     * @param {Object[]} childrenData child nodes data to fetch its descendants
     */
    async _fetchDescendants(childrenData) {
        const resIds = childrenData.map((d) => d.id);
        if (resIds.length) {
            const fetchChildren = await this.orm.readGroup(
                this.resModel,
                [[this.parentFieldName, "in", resIds]],
                ['id:array_agg'],
                [this.parentFieldName],
                { context: this.config.context || {} },
            );
            const childIdsPerId = Object.fromEntries(
                fetchChildren.map((r) => [r[this.parentFieldName][0], r.id])
            );
            for (const d of childrenData) {
                if (d.id.toString() in childIdsPerId) {
                    d[this.defaultChildFieldName] = childIdsPerId[d.id.toString()];
                }
            }
        }
    }

    async updateParentNode(nodeId, { parentNodeId, parentResId }) {
        const node = this.root.nodePerNodeId[nodeId];
        const parentNode = parentNodeId ? this.root.nodePerNodeId[parentNodeId] : null;
        if (node) {
            const oldParentNode = node.parentNode;
            let fetchParentChildren = false;
            let domain = new Domain([]);
            if (oldParentNode) {
                domain = new Domain([["id", "=", oldParentNode.resId]]);
            }
            if (parentNode) {
                if (parentNode.resId === node.resId) {
                    this.notification.add(
                        _t("The parent record cannot be the record dragged."),
                        {
                            type: "danger",
                        }
                    );
                    return;
                } else if (node.allSubsidiaryResIds.includes(parentNode.resId)) {
                    this.notification.add(
                        _t("Cannot change the parent because it will cause a cyclic."),
                        {
                            type: "danger",
                        }
                    );
                    return;
                }
                domain = Domain.or([
                    domain,
                    [["id", "in", [parentNode.resId, node.resId]]],
                ]);
                if (parentNode.nodes.length === 0 && parentNode.childResIds.length > 0) {
                    fetchParentChildren = true;
                    domain = Domain.or([
                        domain,
                        [[this.parentFieldName, "=", parentNode.resId], ["id", "!=", node.resId]],
                    ]);
                }
                if (node.id === node.tree.root.id) {
                    this.root.removeTree(node.tree);
                    node.tree = parentNode.tree;
                } else {
                    node.removeParentNode();
                }
            } else {
                node.removeParentNode();
                this.root.addNewRootNode(node);
            }
            this.notify();
            await this.mutex.exec(async () => {
                await this.orm.write(
                    this.resModel,
                    [node.resId],
                    { [this.parentFieldName]: parentResId || parentNode?.resId || false },
                    { context: this.config.context }
                );
            });
            domain = domain.toList({});
            if (domain.length) {
                const data = await this.orm.searchRead(
                    this.resModel,
                    domain,
                    this.fieldsToFetch,
                    { context: this.config.context },
                );
                const children = [];
                for (const d of data) {
                    if (d.id === node.resId) {
                        node.data = d;
                    } else if (d.id === oldParentNode?.resId) {
                        oldParentNode.data = d;
                    } else if (parentNode) {
                        if (parentNode.resId === d.id) {
                            const parentData = fetchParentChildren ? {} : pick(parentNode.data, this.childFieldName);
                            parentNode.data = {
                                ...d,
                                ...parentData,
                            };
                        } else if (fetchParentChildren) {
                            children.push(d);
                        }
                    }
                }
                if (children.length) {
                    parentNode.data[this.childFieldName || this.defaultChildFieldName] = children;
                }
            }
            const treeExpanded = this._findTreeExpanded();
            if (parentNode) {
                if (treeExpanded && treeExpanded.id !== parentNode.tree.id) {
                    treeExpanded.root.nodes = [];
                    treeExpanded.nodePerNodeId = { [treeExpanded.root.id]: treeExpanded.root };
                } else if (treeExpanded) {
                    const nodeToCollapse = this._searchNodeToCollapse(parentNode);
                    if (nodeToCollapse && nodeToCollapse.id !== parentNode.id) {
                        nodeToCollapse.collapseChildNodes();
                    }
                }
                if (fetchParentChildren) {
                    parentNode.populateChildNodes();
                }
                node.setParentNode(parentNode);
            } else if (treeExpanded && node.nodes.length) {
                treeExpanded.root.collapseChildNodes();
            }
            this.notify();
        }
    }
}
