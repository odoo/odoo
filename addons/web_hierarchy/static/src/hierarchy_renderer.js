/** @odoo-module */

import { Component, useRef, onPatched } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";

import { HierarchyCard } from "./hierarchy_card";
import { useHierarchyNodeDraggable } from "./hierarchy_node_draggable";

export class HierarchyRenderer extends Component {
    static components = {
        HierarchyCard,
    };
    static props = {
        model: Object,
        openRecord: Function,
        archInfo: Object,
        templates: Object,
    };
    static template = "web_hierarchy.HierarchyRenderer";

    setup() {
        this.rendererRef = useRef("renderer");
        this.notification = useService("notification");
        if (this.canDragAndDropRecord) {
            useHierarchyNodeDraggable({
                ref: this.rendererRef,
                enable: this.draggable,
                elements: ".o_hierarchy_node_container",
                handle: ".o_hierarchy_node",
                rows: ".o_hierarchy_row",
                ignore: "button",
                onDragStart: ({ addClass, element }) => {
                    addClass(element, "o_hierarchy_dragged");
                    addClass(element.querySelector(".o_hierarchy_node"), "shadow");
                },
                onDragEnd: ({ removeClass, element, row, hierarchyRow }) => {
                    removeClass(element, "o_hierarchy_dragged");
                    if (row) {
                        removeClass(row, "o_hierarchy_hover");
                    }
                    if (hierarchyRow) {
                        removeClass(hierarchyRow, "o_hierarchy_hover");
                    }
                },
                onDrop: (params) => {
                    this.nodeDrop(params);
                },
                onElementEnter: ({ addClass, element }) => {
                    addClass(element, "o_hierarchy_hover");
                },
                onElementLeave: ({ removeClass, element }) => {
                    removeClass(element, "o_hierarchy_hover");
                },
                onRowEnter: ({ addClass, row }) => {
                    addClass(row, "o_hierarchy_hover");
                },
                onRowLeave: ({ removeClass, row }) => {
                    removeClass(row, "o_hierarchy_hover");
                },
            });
        }
        this.scrollTarget = "none";
        useBus(this.props.model.bus, "hierarchyScrollTarget", (ev) => {
            this.scrollTarget = ev.detail?.scrollTarget || "none";
        });
        onPatched(this.onPatched);
    }

    onPatched() {
        if (this.scrollTarget === "none") {
            return;
        }
        const row =
            this.scrollTarget === "bottom"
                ? this.rendererRef.el.querySelector(":scope .o_hierarchy_row:last-child")
                : this.rendererRef.el
                      .querySelector(
                          `:scope .o_hierarchy_node[data-node-id="${this.scrollTarget}"]`
                      )
                      ?.closest(".o_hierarchy_row");
        this.scrollTarget = "none";
        if (!row) {
            return;
        }
        scrollTo(row, { behavior: "smooth" });
    }

    get canDragAndDropRecord() {
        return this.draggable && !this.env.isSmall;
    }

    get draggable() {
        return this.props.archInfo.draggable;
    }

    get rows() {
        const rootNodes = this.props.model.root.rootNodes.filter((n) => !n.hidden);
        const rows = [{ nodes: rootNodes }];
        const processNode = (node, rootNode) => {
            const subNodes = node.nodes.filter((n) => !n.hidden);
            if (subNodes.length && !subNodes.includes(rootNode)) {
                rows.push({ parentNode: node, nodes: subNodes });
                for (const subNode of subNodes) {
                    processNode(subNode, rootNode);
                }
            }
        };

        for (const node of rootNodes) {
            processNode(node, node);
        }

        return rows;
    }

    async nodeDrop({ element, row, nextRow, newParentNode }) {
        let parentNodeId, parentResId;
        if (newParentNode) {
            parentNodeId = newParentNode.dataset.nodeId;
        } else if (nextRow?.dataset.rowId !== row.dataset.rowId) {
            parentNodeId = nextRow.dataset.parentNodeId;
            if (!parentNodeId) {
                const nodes = this.rows[nextRow.dataset.rowId].nodes || [];
                if (nodes) {
                    parentNodeId = nodes[0].parentNode?.id;
                    if (!parentNodeId) {
                        parentResId = nodes[0].parentResId;
                        if (!nodes.every((node) => node.parentResId === parentResId)) {
                            this.notification.add(
                                _t("Impossible to update the parent node of the dragged node because no parent has been found."),
                                {
                                    type: "danger",
                                }
                            );
                            return;
                        }
                    }
                }
            }
        }
        await this.props.model.updateParentNode(element.dataset.nodeId, { parentResId, parentNodeId });
    }
}
