/** @odoo-module */

import { FilterValue } from "@spreadsheet/global_filters/components/filter_value/filter_value";
import { _t } from "@web/core/l10n/translation";
import { Component, useRef } from "@odoo/owl";
import { hooks } from "@odoo/o-spreadsheet";

/**
 * This is the side panel to define/edit a global filter.
 * It can be of 3 different type: text, date and relation.
 */
export class GlobalFiltersSidePanel extends Component {
    dnd = hooks.useDragAndDropListItems();
    filtersListRef = useRef("filtersList");

    setup() {
        this.getters = this.env.model.getters;
    }

    get isReadonly() {
        return this.env.model.getters.isReadonly();
    }

    get filters() {
        return this.env.model.getters.getGlobalFilters();
    }

    _t(...args) {
        return _t(...args);
    }

    hasDataSources() {
        return (
            this.env.model.getters.getPivotIds().length +
            this.env.model.getters.getListIds().length +
            this.env.model.getters.getOdooChartIds().length
        );
    }

    newText() {
        this.env.openSidePanel("TEXT_FILTER_SIDE_PANEL");
    }

    newDate() {
        this.env.openSidePanel("DATE_FILTER_SIDE_PANEL");
    }

    newRelation() {
        this.env.openSidePanel("RELATION_FILTER_SIDE_PANEL");
    }

    /**
     * @param {string} id
     */
    onEdit(id) {
        const filter = this.env.model.getters.getGlobalFilter(id);
        if (!filter) {
            return;
        }
        switch (filter.type) {
            case "text":
                this.env.openSidePanel("TEXT_FILTER_SIDE_PANEL", { id });
                break;
            case "date":
                this.env.openSidePanel("DATE_FILTER_SIDE_PANEL", { id });
                break;
            case "relation":
                this.env.openSidePanel("RELATION_FILTER_SIDE_PANEL", { id });
                break;
        }
    }

    startDragAndDrop(filter, event) {
        if (event.button !== 0) {
            return;
        }

        const rects = this.getFiltersElementsRects();
        const filtersItems = this.filters.map((filter, index) => ({
            id: filter.id,
            size: rects[index].height,
            position: rects[index].y,
        }));
        this.dnd.start("vertical", {
            draggedItemId: filter.id,
            initialMousePosition: event.clientY,
            items: filtersItems,
            containerEl: this.filtersListRef.el,
            onDragEnd: (filterId, finalIndex) => this.onDragEnd(filterId, finalIndex),
        });
    }

    getFiltersElementsRects() {
        return Array.from(this.filtersListRef.el.children).map((filterEl) =>
            filterEl.getBoundingClientRect()
        );
    }

    getFilterItemStyle(filter) {
        return this.dnd.itemsStyle[filter.id] || "";
    }

    onDragEnd(filterId, finalIndex) {
        const originalIndex = this.filters.findIndex((filter) => filter.id === filterId);
        const delta = finalIndex - originalIndex;
        if (filterId && delta !== 0) {
            this.env.model.dispatch("MOVE_GLOBAL_FILTER", {
                id: filterId,
                delta,
            });
        }
    }
}

GlobalFiltersSidePanel.template = "spreadsheet_edition.GlobalFiltersSidePanel";
GlobalFiltersSidePanel.components = { FilterValue };
GlobalFiltersSidePanel.props = {
    onCloseSidePanel: { type: Function, optional: true },
};
