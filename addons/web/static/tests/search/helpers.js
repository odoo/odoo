/** @odoo-module **/

import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { CustomFavoriteItem } from "@web/search/favorite_menu/custom_favorite_item";
import { WithSearch } from "@web/search/with_search/with_search";
import { viewService } from "@web/views/view_service";
import { actionService } from "@web/webclient/actions/action_service";
import { registerCleanup } from "../helpers/cleanup";
import { makeTestEnv } from "../helpers/mock_env";
import { click, getFixture, mouseEnter, triggerEvent } from "../helpers/utils";

const serviceRegistry = registry.category("services");
const favoriteMenuRegistry = registry.category("favoriteMenu");

const { Component, mount } = owl;

export const setupControlPanelServiceRegistry = () => {
    serviceRegistry.add("action", actionService);
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("notification", notificationService);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("view", viewService);
};

export const setupControlPanelFavoriteMenuRegistry = () => {
    favoriteMenuRegistry.add(
        "custom-favorite-item",
        { Component: CustomFavoriteItem, groupNumber: 3 },
        { sequence: 0 }
    );
};

export const makeWithSearch = async (params) => {
    const props = { ...params };

    const serverData = props.serverData || undefined;
    const mockRPC = props.mockRPC || undefined;
    const config = props.config || {};

    delete props.serverData;
    delete props.mockRPC;
    delete props.config;

    const env = await makeTestEnv({ serverData, mockRPC, config });

    const target = getFixture();
    const withSearch = await mount(WithSearch, { env, props, target });

    registerCleanup(() => withSearch.destroy());

    const component = Object.values(withSearch.__owl__.children)[0];

    return component;
};

const getNode = (target) => {
    return target instanceof Component ? target.el : target;
};

const findItem = (target, selector, finder = 0) => {
    const el = getNode(target);
    const elems = [...el.querySelectorAll(selector)];
    if (Number.isInteger(finder)) {
        return elems[finder];
    }
    return elems.find((el) => el.innerText.trim().toLowerCase() === finder.toLowerCase());
};

/** Menu (generic) */

export const toggleMenu = async (el, menuFinder) => {
    const menu = findItem(el, `.dropdown button.dropdown-toggle`, menuFinder);
    await click(menu);
};

export const toggleMenuItem = async (el, itemFinder) => {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    if (item.classList.contains("dropdown-toggle")) {
        await mouseEnter(item);
    } else {
        await click(item);
    }
};
export const toggleMenuItemOption = async (el, itemFinder, optionFinder) => {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    const option = findItem(item.parentNode, ".o_item_option", optionFinder);
    if (option.classList.contains("dropdown-toggle")) {
        await mouseEnter(option);
    } else {
        await click(option);
    }
};
export const isItemSelected = (el, itemFinder) => {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    return item.classList.contains("selected");
};
export const isOptionSelected = (el, itemFinder, optionFinder) => {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    const option = findItem(item.parentNode, ".o_item_option", optionFinder);
    return option.classList.contains("selected");
};
export const getMenuItemTexts = (target) => {
    const el = getNode(target);
    return [...el.querySelectorAll(`.dropdown ul .o_menu_item`)].map((e) => e.innerText.trim());
};

/** Filter menu */

export const toggleFilterMenu = async (el) => {
    await click(findItem(el, `.o_filter_menu button.dropdown-toggle`));
};

export const toggleAddCustomFilter = async (el) => {
    await mouseEnter(findItem(el, `.o_add_custom_filter_menu .dropdown-toggle`));
};

export const editConditionField = async (el, index, fieldName) => {
    const condition = findItem(el, `.o_filter_condition`, index);
    const select = findItem(condition, "select", 0);
    select.value = fieldName;
    await triggerEvent(select, null, "change");
};

export const editConditionOperator = async (el, index, operator) => {
    const condition = findItem(el, `.o_filter_condition`, index);
    const select = findItem(condition, "select", 1);
    select.value = operator;
    await triggerEvent(select, null, "change");
};

export const editConditionValue = async (el, index, value, valueIndex = 0) => {
    const condition = findItem(el, `.o_filter_condition`, index);
    const target = findItem(
        condition,
        ".o_generator_menu_value input,.o_generator_menu_value select",
        valueIndex
    );
    target.value = value;
    await triggerEvent(target, null, "change");
};

export const applyFilter = async (el) => {
    await click(findItem(el, `.o_add_custom_filter_menu .dropdown-menu button.o_apply_filter`));
};

export const addCondition = async (el) => {
    await click(findItem(el, `.o_add_custom_filter_menu .dropdown-menu button.o_add_condition`));
};

export async function removeCondition(el, index) {
    const condition = findItem(el, `.o_filter_condition`, index);
    await click(findItem(condition, ".o_generator_menu_delete"));
}

/** Group by menu */

export const toggleGroupByMenu = async (el) => {
    await click(findItem(el, `.o_group_by_menu .dropdown-toggle`));
};

export const toggleAddCustomGroup = async (el) => {
    await mouseEnter(findItem(el, `.o_add_custom_group_menu .dropdown-toggle`));
};

export const selectGroup = async (el, fieldName) => {
    const select = findItem(el, `.o_add_custom_group_menu .dropdown-menu select`);
    select.value = fieldName;
    await triggerEvent(select, null, "change");
};

export const applyGroup = async (el) => {
    await click(findItem(el, `.o_add_custom_group_menu .dropdown-menu .btn`));
};

/** Favorite menu */

export const toggleFavoriteMenu = async (el) => {
    await click(findItem(el, `.o_favorite_menu .dropdown-toggle`));
};

export const deleteFavorite = async (el, favoriteFinder) => {
    const favorite = findItem(el, `.o_favorite_menu .o_menu_item`, favoriteFinder);
    await click(findItem(favorite, "i.fa-trash-o"));
};

export const toggleSaveFavorite = async (el) => {
    await mouseEnter(findItem(el, `.o_favorite_menu .o_add_favorite .dropdown-toggle`));
};

export const editFavoriteName = async (el, name) => {
    const input = findItem(
        el,
        `.o_favorite_menu .o_add_favorite .dropdown-menu input[type="text"]`
    );
    input.value = name;
    await triggerEvent(input, null, "input");
};

export const saveFavorite = async (el) => {
    await click(findItem(el, `.o_favorite_menu .o_add_favorite .dropdown-menu button`));
};

/** Comparison menu */

export const toggleComparisonMenu = async (el) => {
    await click(findItem(el, `.o_comparison_menu button.dropdown-toggle`));
};

/** Search bar */

export const getFacetTexts = (target) => {
    const el = getNode(target);
    return [...el.querySelectorAll(`div.o_searchview_facet`)].map((facet) =>
        facet.innerText.trim()
    );
};

export const removeFacet = async (el, facetFinder = 0) => {
    const facet = findItem(el, `div.o_searchview_facet`, facetFinder);
    await click(facet.querySelector("i.o_facet_remove"));
};

export const editSearch = async (el, value) => {
    const input = findItem(el, `.o_searchview input`);
    input.value = value;
    await triggerEvent(input, null, "input");
};

export const validateSearch = async (el) => {
    const input = findItem(el, `.o_searchview input`);
    await triggerEvent(input, null, "keydown", { key: "Enter" });
};

/** Switch View */

export const switchView = async (el, viewType) => {
    await click(findItem(el, `button.o_switch_view.o_${viewType}`));
};

/////////////////////////////////////
// Action Menu
/////////////////////////////////////
// /**
//  * @param {EventTarget} el
//  * @param {string} [menuFinder="Action"]
//  * @returns {Promise}
//  */
// export async function toggleActionMenu(el, menuFinder = "Action") {
//     const dropdown = findItem(el, `.o_cp_action_menus button`, menuFinder);
//     await click(dropdown);
// }
/////////////////////////////////////
// Pager
/////////////////////////////////////
// /**
//  * @param {EventTarget} el
//  * @returns {Promise}
//  */
// export async function pagerPrevious(el) {
//     await click(getNode(el).querySelector(`.o_pager button.o_pager_previous`));
// }
// /**
//  * @param {EventTarget} el
//  * @returns {Promise}
//  */
// export async function pagerNext(el) {
//     await click(getNode(el).querySelector(`.o_pager button.o_pager_next`));
// }
// /**
//  * @param {EventTarget} el
//  * @returns {string}
//  */
// export function getPagerValue(el) {
//     const pagerValue = getNode(el).querySelector(`.o_pager_counter .o_pager_value`);
//     switch (pagerValue.tagName) {
//         case 'INPUT':
//             return pagerValue.value;
//         case 'SPAN':
//             return pagerValue.innerText.trim();
//     }
// }
// /**
//  * @param {EventTarget} el
//  * @returns {string}
//  */
// export function getPagerSize(el) {
//     return getNode(el).querySelector(`.o_pager_counter span.o_pager_limit`).innerText.trim();
// }
// /**
//  * @param {EventTarget} el
//  * @param {string} value
//  * @returns {Promise}
//  */
// export async function setPagerValue(el, value) {
//     let pagerValue = getNode(el).querySelector(`.o_pager_counter .o_pager_value`);
//     if (pagerValue.tagName === 'SPAN') {
//         await click(pagerValue);
//     }
//     pagerValue = getNode(el).querySelector(`.o_pager_counter input.o_pager_value`);
//     if (!pagerValue) {
//         throw new Error("Pager value is being edited and cannot be changed.");
//     }
//     await editAndTrigger(pagerValue, value, ['change', 'blur']);
// }
