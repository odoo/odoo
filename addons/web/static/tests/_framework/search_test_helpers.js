/** @odoo-module */

import { queryAll, queryAllTexts, queryContent, queryOne } from "@odoo/hoot-dom";
import { contains } from "./dom_test_helpers";
import { getMockEnv } from "./env_test_helpers";

const ensureSearchView = async () => {
    if (getMockEnv().isSmall && !queryAll`.o_searchview`.length) {
        await contains(`.o_control_panel_navigation button`).click();
    }
};

const ensureSearchBarMenu = async () => {
    if (!queryAll`.o_search_bar_menu`.length) {
        await toggleSearchBarMenu();
    }
};

//-----------------------------------------------------------------------------
// Menu (generic)
//-----------------------------------------------------------------------------

/**
 * @param {string} label
 */
export async function toggleMenu(label) {
    await contains(`.dropdown button.dropdown-toggle:contains(/^${label}$/)`).click();
}

/**
 * @param {string} label
 */
export async function toggleMenuItem(label) {
    const target = queryOne`.o_menu_item:contains(/^${label}$/)`;
    if (target.classList.contains("dropdown-toggle")) {
        await contains(target).hover();
    } else {
        await contains(target).click();
    }
}

/**
 * @param {string} itemLabel
 * @param {string} optionLabel
 */
export async function toggleMenuItemOption(itemLabel, optionLabel) {
    const { parentElement } = queryOne`.o_menu_item:contains(/^${itemLabel}$/)`;
    const target = queryOne(`.o_item_option:contains(/^${optionLabel}$/)`, {
        root: parentElement,
    });
    if (target.classList.contains("dropdown-toggle")) {
        await contains(target).hover();
    } else {
        await contains(target).click();
    }
}

/**
 * @param {string} label
 */
export function isItemSelected(label) {
    return queryOne`.o_menu_item:contains(/^${label}$/)`.classList.contains("selected");
}

/**
 * @param {string} itemLabel
 * @param {string} optionLabel
 */
export function isOptionSelected(itemLabel, optionLabel) {
    const { parentElement } = queryOne`.o_menu_item:contains(/^${itemLabel}$/)`;
    return queryOne(`.o_item_option:contains(/^${optionLabel}$/)`, {
        root: parentElement,
    }).classList.contains("selected");
}

export function getMenuItemTexts() {
    return queryAllTexts`.dropdown-menu .o_menu_item`;
}

export function getButtons() {
    return queryAll`.o_control_panel_breadcrumbs button`;
}

export function getVisibleButtons() {
    return queryAll`.o_control_panel_breadcrumbs button:visible, .o_control_panel_actions button:visible`;
}

//-----------------------------------------------------------------------------
// Filter menu
//-----------------------------------------------------------------------------

export async function toggleFilterMenu() {
    await ensureSearchBarMenu();
    await contains(`.o_filter_menu button.dropdown-toggle`).click();
}

export async function openAddCustomFilterDialog() {
    await ensureSearchBarMenu();
    await contains(`.o_filter_menu .o_menu_item.o_add_custom_filter`).click();
}

//-----------------------------------------------------------------------------
// Group by menu
//-----------------------------------------------------------------------------

export async function toggleGroupByMenu() {
    await ensureSearchBarMenu();
    await contains(`.o_group_by_menu .dropdown-toggle`).click();
}

/**
 * @param {string} fieldName
 */
export async function selectGroup(fieldName) {
    await ensureSearchBarMenu();
    await contains(`.o_add_custom_group_menu`).edit(fieldName);
}

//-----------------------------------------------------------------------------
// Favorite menu
//-----------------------------------------------------------------------------

export async function toggleFavoriteMenu() {
    await ensureSearchBarMenu();
    await contains(`.o_favorite_menu .dropdown-toggle`).click();
}

/**
 * @param {string} text
 */
export async function deleteFavorite(text) {
    await ensureSearchBarMenu();
    await contains(`.o_favorite_menu .o_menu_item:contains(/^${text}$/) i.fa-trash-o`).click();
}

export async function toggleSaveFavorite() {
    await ensureSearchBarMenu();
    await contains(`.o_favorite_menu .o_add_favorite`).click();
}

/**
 * @param {string} name
 */
export async function editFavoriteName(name) {
    await ensureSearchBarMenu();
    await contains(
        `.o_favorite_menu .o_add_favorite + .o_accordion_values input[type="text"]`
    ).edit(name, { confirm: false });
}

export async function saveFavorite() {
    await ensureSearchBarMenu();
    await contains(`.o_favorite_menu .o_add_favorite + .o_accordion_values button`).click();
}

//-----------------------------------------------------------------------------
// Comparison menu
//-----------------------------------------------------------------------------

export async function toggleComparisonMenu() {
    await ensureSearchBarMenu();
    await contains(`.o_comparison_menu button.dropdown-toggle`).click();
}

//-----------------------------------------------------------------------------
// Search bar
//-----------------------------------------------------------------------------

export function getFacetTexts() {
    return queryAllTexts(`.o_searchview_facet`);
}

/**
 * @param {string} label
 */
export async function removeFacet(label) {
    await ensureSearchView();
    await contains(`.o_searchview_facet:contains(/^${label}$/) .o_facet_remove`).click();
}

/**
 * @param {string} value
 */
export async function editSearch(value) {
    await ensureSearchView();
    await contains(`.o_searchview input`).edit(value);
}

export async function validateSearch() {
    await ensureSearchView();
    await contains(`.o_searchview input`).press("Enter");
}

//-----------------------------------------------------------------------------
// Switch view
//-----------------------------------------------------------------------------

/**
 * @param {import("./mock_server/mock_server").ViewType} viewType
 */
export async function switchView(viewType) {
    await contains(`button.o_switch_view.o_${viewType}`).click();
}

//-----------------------------------------------------------------------------
// Pager
//-----------------------------------------------------------------------------

export function getPagerValue() {
    return queryContent(".o_pager .o_pager_value")
        .split(/\s*-\s*/)
        .map(Number);
}

export function getPagerLimit() {
    return queryContent(".o_pager .o_pager_limit");
}

export async function pagerNext() {
    await contains(".o_pager button.o_pager_next").click();
}

export async function pagerPrevious() {
    await contains(".o_pager button.o_pager_previous").click();
}

/**
 * @param {string} value
 */
export async function editPager(value) {
    await contains(`.o_pager .o_pager_limit`).edit(value);
}

//-----------------------------------------------------------------------------
// Action Menu
//-----------------------------------------------------------------------------

/**
 * @param {EventTarget} el
 * @param {string} [menuFinder="Action"]
 * @returns {Promise}
 */
export async function toggleActionMenu() {
    await contains(".o_cp_action_menus .dropdown-toggle").click();
}

//-----------------------------------------------------------------------------
// Search bar menu
//-----------------------------------------------------------------------------

export async function toggleSearchBarMenu() {
    await ensureSearchView();
    await contains(`.o_searchview_dropdown_toggler`).click();
}
