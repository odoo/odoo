// @ts-check

/** @module @web/fields/display/progress_bar/kanban_progress_bar_field - Kanban-view variant of the progress bar field */

import { registry } from "@web/core/registry";

import { ProgressBarField, progressBarField } from "./progress_bar_field";
export class KanbanProgressBarField extends ProgressBarField {
    /** @returns {boolean} Whether the bar is editable (ignores readonly, unlike parent). */
    get isEditable() {
        return this.props.isEditable;
    }
}

export const kanbanProgressBarField = {
    ...progressBarField,
    component: KanbanProgressBarField,
};

registry.category("fields").add("kanban.progressbar", kanbanProgressBarField);
