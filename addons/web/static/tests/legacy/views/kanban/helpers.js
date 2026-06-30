/** @odoo-module alias=@web/../tests/views/kanban/helpers default=false */

import { makeFakeDialogService } from "@web/../tests/helpers/mock_services";
import { click, editInput, getDropdownMenu, nextTick } from "@web/../tests/helpers/utils";

import { registry } from "@web/core/registry";

export function patchDialog(addDialog) {
    registry.category("services").add("dialog", makeFakeDialogService(addDialog), { force: true });
}

// Kanban
// WOWL remove this helper and use the control panel instead
export async function reload(kanban, params = {}) {
    kanban.env.searchModel.reload(params);
    kanban.env.searchModel.search();
    await nextTick();
}

export function getCard(target, cardIndex = 0) {
    return target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")[cardIndex];
}

export function getColumn(target, groupIndex = 0, ignoreFolded = false) {
    let selector = ".o_kanban_group";
    if (ignoreFolded) {
        selector += ":not(.o_column_folded)";
    }
    return target.querySelectorAll(selector)[groupIndex];
}

export function getColumnDropdownMenu(target, groupIndex = 0, ignoreFolded = false) {
    let selector = ".o_kanban_group";
    if (ignoreFolded) {
        selector += ":not(.o_column_folded)";
    }
    const column = target.querySelectorAll(selector)[groupIndex];
    return getDropdownMenu(target, column);
}

export function getCardTexts(target, groupIndex) {
    const root = groupIndex >= 0 ? getColumn(target, groupIndex) : target;
    return [...root.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")]
        .map((card) => card.innerText.trim())
        .filter(Boolean);
}

export function getCounters(target) {
    return [...target.querySelectorAll(".o_animated_number")].map((counter) => counter.innerText);
}

export function getProgressBars(target, columnIndex) {
    const column = getColumn(target, columnIndex);
    return [...column.querySelectorAll(".o_column_progress .progress-bar")];
}

export function getTooltips(target, groupIndex) {
    const root = groupIndex >= 0 ? getColumn(target, groupIndex) : target;
    return [...root.querySelectorAll(".o_column_progress .progress-bar")]
        .map((card) => card.dataset.tooltip)
        .filter(Boolean);
}

// Record
export async function createRecord(target) {
    await click(target, ".o_control_panel_main_buttons button.o-kanban-button-new");
    await nextTick();
}

export async function quickCreateRecord(target, groupIndex) {
    await click(getColumn(target, groupIndex), ".o_kanban_quick_add");
    await nextTick();
}

export async function editQuickCreateInput(target, field, value) {
    await editInput(target, `.o_kanban_quick_create .o_field_widget[name=${field}] input`, value);
}

export async function validateRecord(target) {
    await click(target, ".o_kanban_quick_create .o_kanban_add");
}

export async function editRecord(target) {
    await click(target, ".o_kanban_quick_create .o_kanban_edit");
}

export async function discardRecord(target) {
    await click(target, ".o_kanban_quick_create .o_kanban_cancel");
}

export async function toggleRecordDropdown(target, recordIndex) {
    const group = target.querySelectorAll(`.o_kanban_record`)[recordIndex];
    await click(group, ".o_dropdown_kanban .dropdown-toggle");
}

// Column
export async function createColumn(target) {
    await click(target, ".o_column_quick_create > .o_quick_create_folded");
}

export async function editColumnName(target, value) {
    await editInput(target, ".o_column_quick_create input", value);
}

export async function validateColumn(target) {
    await click(target, ".o_column_quick_create .o_kanban_add");
}

export async function loadMore(target, columnIndex) {
    await click(getColumn(target, columnIndex), ".o_kanban_load_more button");
}
