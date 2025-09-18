// @ts-check

/** @module @web/views/view_components/selection_box - Banner with "Select all matching" and "Unselect" actions shown when records are selected */

import { Component } from "@odoo/owl";

/** Banner shown above a list/kanban when records are selected, offering "Select all matching" and "Unselect" actions. */
export class SelectionBox extends Component {
    static components = {};
    static template = "web.SelectionBox";
    static props = {
        root: { type: Object },
    };
    setup() {
        this.root = this.props.root;
    }
    /** @returns {number} count of currently selected records */
    get nbSelected() {
        return this.selectedRecords.length;
    }
    /** @returns {number} total record count (grouped or ungrouped) */
    get nbTotal() {
        return this.root.isGrouped ? this.root.recordCount : this.root.count;
    }
    /** @returns {boolean} whether the total count is approximate (limited) */
    get hasLimitedCount() {
        return this.root.hasLimitedCount;
    }
    /** @returns {boolean} whether all records matching the domain are selected */
    get isDomainSelected() {
        return this.root.isDomainSelected;
    }
    /** @returns {boolean} whether all records on the current page are selected but more exist */
    get isPageSelected() {
        return (
            this.nbSelected === this.root.records.length &&
            (!this.isRecordCountTrustable || this.nbTotal > this.selectedRecords.length)
        );
    }
    /** @returns {boolean} whether the total record count is exact (not estimated) */
    get isRecordCountTrustable() {
        return this.root.isRecordCountTrustable;
    }
    /** @returns {Array<Object>} list of currently selected record objects */
    get selectedRecords() {
        return this.root.selection;
    }
    /** Deselect all records and clear domain selection. */
    onUnselectAll() {
        this.selectedRecords.forEach((record) => {
            record.toggleSelection(false);
        });
        this.root.selectDomain(false);
    }
    /** Extend selection to all records matching the current domain (beyond the current page). */
    onSelectDomain() {
        this.root.selectDomain(true);
    }
}
