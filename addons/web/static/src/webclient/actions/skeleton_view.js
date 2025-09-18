// @ts-check

/** @module @web/webclient/actions/skeleton_view - Shimmer loading placeholder shown during view transitions to replace blank screens */

import { Component, onMounted } from "@odoo/owl";

/**
 * Skeleton loading placeholder shown during view transitions.
 *
 * Replaces the blank white screen during clearBreadcrumbs navigation
 * with shimmer placeholders that match the target view's layout structure.
 */
export class SkeletonView extends Component {
    static template = "web.SkeletonView";
    static props = {
        onMounted: Function,
        viewType: { type: String, optional: true },
        withControlPanel: { type: Boolean, optional: true },
        "*": true,
    };

    /** Initialize pre-built arrays for template loops and register onMounted callback. */
    setup() {
        // Pre-built arrays for t-foreach loops (OWL templates lack range())
        /** @type {number[]} */
        this.listRows = Array.from({ length: 8 }, (_, i) => i);
        /** @type {number[]} */
        this.listCols = Array.from({ length: 5 }, (_, i) => i);
        /** @type {number[]} */
        this.kanbanCards = Array.from({ length: 3 }, (_, i) => i);
        /** @type {number[]} */
        this.kanbanGroups = Array.from({ length: 3 }, (_, i) => i);
        /** @type {number[]} */
        this.formFields = Array.from({ length: 6 }, (_, i) => i);
        onMounted(() => this.props.onMounted());
    }

    /** @returns {string} The view type to render, defaulting to "generic". */
    get viewType() {
        return this.props.viewType || "generic";
    }

    /**
     * Vary skeleton bar widths to look organic, not uniform.
     * @param {number} row - Row index
     * @param {number} col - Column index
     * @returns {number} Width percentage between 35 and 80
     */
    cellWidth(row, col) {
        return 35 + ((row * 7 + col * 13) % 45);
    }
}
