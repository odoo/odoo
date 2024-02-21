/** @odoo-module **/

import { ListRenderer } from '@web/views/list/list_renderer';

import { useState } from "@odoo/owl";

export class NotebookTaskListRenderer extends ListRenderer {
    static rowsTemplate = "project.NotebookTaskListRenderer.Rows";
    setup() {
        super.setup();
        this.hideState = useState({
            hide: localStorage.getItem(this._getStorageKey) == 'true' || false,
        });
    }

    /**
     * @private
     * @returns {string}
     */
    get _getStorageKey() {
        return `hide_closed_${this.constructor.name}`;
    }

    get hideClosed() {
        return this.hideState.hide
    }

    get closedX2MCount() {
        return this.props.list.context.closed_X2M_count;
    }

    get openLabel() {
        return `${typeof this.closedX2MCount === 'undefined' ? 'Show' : this.closedX2MCount} closed task` + (this.closedX2MCount > 1 ? "s" : "");
    }

    get closeLabel() {
        return 'Hide closed task' + (this.closedX2MCount > 1 ? "s" : "");
    }

    get toggleLabel() {
        return this.hideClosed ? this.openLabel : this.closeLabel;
    }

    get ShowX2MRecords() {
        // If there isn't a closed_X2M_count defined in the context of the x2m task in the view we are always displaying the Toggle button
        // In case there is no computed field to calculate the number of closed X2M tasks in the backend
        return this.closedX2MCount > 0 || typeof this.closedX2MCount === 'undefined';
    }

    toggleHideClosed() {
        this.hideState.hide = !this.hideState.hide;
        localStorage.setItem(this._getStorageKey, this.hideState.hide);
        document.activeElement.blur();
    }
}
