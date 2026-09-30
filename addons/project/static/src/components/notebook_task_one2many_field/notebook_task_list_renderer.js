import { useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";

import { TaskListRenderer } from "../task_list_renderer";

export class NotebookTaskListRenderer extends TaskListRenderer {
    static rowsTemplate = "project.NotebookTaskListRenderer.Rows";
    setup() {
        super.setup();
        this.hideState = useState({
            hide: localStorage.getItem(this._getStorageKey) === 'true',
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
        return this.hideState.hide;
    }

    get closedX2MCount() {
        return this.props.list.context.closed_X2M_count;
    }

    get openLabel() {
        return typeof this.closedX2MCount === "undefined" ? _t("Show closed tasks") : _t("%s closed tasks", this.closedX2MCount);
    }

    get closeLabel() {
        return _t("Hide closed tasks");
    }

    get toggleListHideLabel() {
        return this.hideClosed ? this.openLabel : this.closeLabel;
    }

    get ShowX2MRecords() {
        // If there isn't a closed_X2M_count defined in the context of the x2m task in the view we are always displaying the Toggle button
        // In case there is no computed field to calculate the number of closed X2M tasks in the backend
        return this.closedX2MCount > 0 || typeof this.closedX2MCount === "undefined";
    }

    toggleHideClosed() {
        this.hideState.hide = !this.hideState.hide;
        localStorage.setItem(this._getStorageKey, this.hideState.hide);
        document.activeElement.blur();
    }
}
