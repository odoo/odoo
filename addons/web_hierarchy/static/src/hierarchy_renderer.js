import { Component, onPatched, signal, t, useProps } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useBus, useService } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";

import { HierarchyCard } from "./hierarchy_card";
import { useHierarchyNodeDraggable } from "./hierarchy_node_draggable";

export class HierarchyRenderer extends Component {
    static template = "web_hierarchy.HierarchyRenderer";
    static components = { HierarchyCard };

    props = useProps({
        model: t.object(),
        openRecord: t.function(),
        archInfo: t.object(),
    });

    rendererRef = signal.ref();

    setup() {
        this.notification = useService("notification");
        this.uiService = useService("ui");
        if (this.canDragAndDropRecord) {
            useHierarchyNodeDraggable({
                ref: this.rendererRef,
                enable: this.props.archInfo.draggable,
                elements: '.o_hierarchy_node_container',
                handle: '.o_hierarchy_node',
                rows: '.o_hierarchy_row',
                ignore: 'button',
                onDragStart: ({ addClass, element }) => {
                    addClass(element, 'o_hierarchy_dragged');
                    addClass(element.querySelector('.o_hierarchy_node'), 'shadow');
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
        let row;
        const rendererEl = this.rendererRef();
        switch (this.scrollTarget) {
            case "none":
                return;
            case "bottom":
                row = rendererEl.querySelector(":scope .o_hierarchy_row:last-child");
                break;
            case "up":
                row = rendererEl.querySelector(":scope .o_hierarchy_row:first-child");
                break;
            default:
                row = rendererEl
                    .querySelector(`:scope .o_hierarchy_node[data-node-id="${this.scrollTarget}"]`)
                    ?.closest(".o_hierarchy_row");
        }
        this.scrollTarget = "none";
        if (!row) {
            return;
        }
        scrollTo(row, { behavior: "smooth" });
    }

    get canDragAndDropRecord() {
        return this.draggable && !this.uiService.isSmall;
    }

    get draggable() {
        return this.props.archInfo.draggable;
    }

    async nodeDrop({ element, row, nextRow, newParentNode }) {
        const elementId = element.querySelector('article').dataset.id;
        const record = this.props.model.root.records.find((r) => r.id === elementId);
        
        let parentResId;
        if (newParentNode) {
            const parentId = newParentNode.querySelector('article').dataset.id;
            parentResId = this.props.model.root.records.find((r) => r.id === parentId).resId;
        } else if (nextRow?.dataset.rowId !== row.dataset.rowId) {
            parentResId = this.props.model.root.groups.find((g) => g.id === nextRow.dataset.rowId).value;
        }

        await this.props.model.updateParent(record, parentResId);
        //await this.props.model.load();
    }
}
