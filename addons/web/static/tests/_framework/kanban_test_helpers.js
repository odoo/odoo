import { animationFrame, queryAll, queryAllAttributes, queryAllTexts, queryOne } from "@odoo/hoot";
import { getDropdownMenu } from "./component_test_helpers";
import { contains } from "./dom_test_helpers";
import { buildSelector } from "./view_test_helpers";

/**
 * @param {number} [columnIndex=0]
 */
export function clickKanbanLoadMore(columnIndex = 0) {
    return contains(".o_kanban_load_more button", { root: getKanbanColumn(columnIndex) }).click();
}

/**
 * @param {SelectorOptions} [options]
 */
export async function clickKanbanRecord(options) {
    await contains(buildSelector(`.o_kanban_record`, options)).click();
}

export async function createKanbanRecord() {
    await contains(".o_control_panel_main_buttons button.o-kanban-button-new").click();
    return animationFrame(); // the kanban quick create is rendered in a second animation frame
}

export function discardKanbanRecord() {
    return contains(".o_kanban_quick_create .o_kanban_cancel").click();
}

/**
 * @param {string} value
 */
export function editKanbanColumnName(value) {
    return contains(".o_column_quick_create input").edit(value);
}

export function editKanbanRecord() {
    return contains(".o_kanban_quick_create .o_kanban_edit").click();
}

/**
 * @param {string} fieldName
 * @param {string} value
 */
export function editKanbanRecordQuickCreateInput(fieldName, value) {
    return contains(`.o_kanban_quick_create .o_field_widget[name=${fieldName}] input`).edit(value, {
        confirm: "tab",
    });
}

/**
 * @param {number} [columnIndex=0]
 * @param {boolean} [ignoreFolded=false]
 */
export function getKanbanColumn(columnIndex = 0, ignoreFolded = false) {
    let selector = ".o_kanban_group";
    if (ignoreFolded) {
        selector += ":not(.o_column_folded)";
    }
    return queryAll(selector).at(columnIndex);
}

/**
 * @param {number} [columnIndex=0]
 * @param {boolean} [ignoreFolded=false]
 */
export function getKanbanColumnDropdownMenu(columnIndex = 0, ignoreFolded = false) {
    const column = getKanbanColumn(columnIndex, ignoreFolded);
    return getDropdownMenu(column);
}

/**
 * @param {number} [columnIndex]
 */
export function getKanbanColumnTooltips(columnIndex) {
    queryAllAttributes;
    const root = columnIndex >= 0 && getKanbanColumn(columnIndex);
    return queryAllAttributes(".o_column_progress .progress-bar", "data-tooltip", { root });
}

export function getKanbanCounters() {
    return queryAllTexts(".o_animated_number");
}

/**
 * @param {number} [columnIndex=0]
 */
export function getKanbanProgressBars(columnIndex = 0) {
    const column = getKanbanColumn(columnIndex);
    return queryAll(".o_column_progress .progress-bar", { root: column });
}

/**
 * @param {SelectorOptions} options
 */
export function getKanbanRecord(options) {
    return queryOne(buildSelector(`.o_kanban_record`, options));
}

/**
 * @param {number} [columnIndex]
 */
export function getKanbanRecordTexts(columnIndex) {
    const root = columnIndex >= 0 && getKanbanColumn(columnIndex);
    return queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)", { root });
}

export function quickCreateKanbanColumn() {
    return contains(".o_column_quick_create > .o_quick_create_folded").click();
}

/**
 * @param {number} [columnIndex=0]
 */
export async function quickCreateKanbanRecord(columnIndex = 0) {
    await contains(".o_kanban_quick_add", { root: getKanbanColumn(columnIndex) }).click();
    return animationFrame(); // the kanban quick create is rendered in a second animation frame
}

/**
 * @param {number} [columnIndex=0]
 */
export async function toggleKanbanColumnActions(columnIndex = 0) {
    const column = getKanbanColumn(columnIndex);
    await contains(".o_kanban_config .dropdown-toggle", { root: column, visible: false }).click();
    return (buttonText) => {
        const menu = getDropdownMenu(column);
        return contains(`.dropdown-item:contains(/\\b${buttonText}\\b/i)`, { root: menu }).click();
    };
}

/**
 * @param {number} [recordIndex=0]
 */
export function toggleKanbanRecordDropdown(recordIndex = 0) {
    return contains(`.o_kanban_record:eq(${recordIndex}) .o_dropdown_kanban .dropdown-toggle`, {
        visible: false,
    }).click();
}

export function validateKanbanColumn() {
    return contains(".o_column_quick_create .o_kanban_add").click();
}

export function validateKanbanRecord() {
    return contains(".o_kanban_quick_create .o_kanban_add").click();
}
