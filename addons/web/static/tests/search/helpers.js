/** @odoo-module **/

import { click } from "../helpers/utils";
import { getFixture, triggerEvent } from "../helpers/utils";
import { makeTestEnv } from "../helpers/mock_env";
import { registerCleanup } from "../helpers/cleanup";
import { WithSearch } from "@web/search/with_search/with_search";

import { actionService } from "@web/webclient/actions/action_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { viewService } from "@web/views/view_service";

import { registry } from "@web/core/registry";

const serviceRegistry = registry.category("services");

const { Component, mount } = owl;

export function setupControlPanelServiceRegistry() {
    serviceRegistry.add("action", actionService);
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("notification", notificationService);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("view", viewService);
}

export async function makeWithSearch(params, props) {
    const serverData = params.serverData || undefined;
    const mockRPC = params.mockRPC || undefined;
    const env = await makeTestEnv({ serverData, mockRPC });
    const target = getFixture();
    const withSearch = await mount(WithSearch, { env, props, target });
    registerCleanup(() => withSearch.destroy());
    const component = Object.values(withSearch.__owl__.children)[0];
    return component;
}

function getNode(target) {
    return target instanceof Component ? target.el : target;
}

function findItem(target, selector, finder = 0) {
    const el = getNode(target);
    const elems = [...el.querySelectorAll(selector)];
    if (Number.isInteger(finder)) {
        return elems[finder];
    }
    return elems.find((el) => el.innerText.trim().toLowerCase() === finder.toLowerCase());
}

/** Menu (generic) */

export async function toggleMenu(el, menuFinder) {
    const menu = findItem(el, `.o_dropdown button.o_dropdown_toggler`, menuFinder);
    await click(menu);
}

export async function toggleMenuItem(el, itemFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    await click(item);
}
export async function toggleMenuItemOption(el, itemFinder, optionFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    const option = findItem(item.parentNode, ".o_item_option", optionFinder);
    await click(option);
}
export function isItemSelected(el, itemFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    return item.classList.contains("active");
}
export function isOptionSelected(el, itemFinder, optionFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    const option = findItem(item.parentNode, ".o_item_option", optionFinder);
    return option.classList.contains("active");
}
export function getMenuItemTexts(target) {
    const el = getNode(target);
    return [...el.querySelectorAll(`.o_dropdown ul .o_menu_item`)].map((e) => e.innerText.trim());
}

/** Filter menu */

export async function toggleFilterMenu(el) {
    await click(findItem(el, `.o_filter_menu button.o_dropdown_toggler`));
}

export async function toggleAddCustomFilter(el) {
    await click(findItem(el, `.o_add_custom_filter_menu .o_dropdown_toggler`));
}

export async function editConditionField(el, index, fieldName) {
    const condition = findItem(el, `.o_filter_condition`, index);
    const select = findItem(condition, "select", 0);
    select.value = fieldName;
    await triggerEvent(select, null, "change");
}

export async function editConditionOperator(el, index, operator) {
    const condition = findItem(el, `.o_filter_condition`, index);
    const select = findItem(condition, "select", 1);
    select.value = operator;
    await triggerEvent(select, null, "change");
}

export async function editConditionValue(el, index, value) {
    const condition = findItem(el, `.o_filter_condition`, index);
    const input = condition.querySelector(".o_generator_menu_value input");
    if (input) {
        input.value = value;
        await triggerEvent(input, null, "input");
    } else {
        const select = findItem(condition, ".o_generator_menu_value select");
        select.value = value;
        await triggerEvent(select, null, "change");
    }
}

export async function applyFilter(el) {
    await click(findItem(el, `.o_add_custom_filter_menu .o_dropdown_menu button.o_apply_filter`));
}

export async function addCondition(el) {
    await click(findItem(el, `.o_add_custom_filter_menu .o_dropdown_menu button.o_add_condition`));
}

/** Group by menu */

export async function toggleGroupByMenu(el) {
    await click(findItem(el, `.o_group_by_menu .o_dropdown_toggler`));
}

export async function toggleAddCustomGroup(el) {
    await click(findItem(el, `.o_add_custom_group_menu .o_dropdown_toggler`));
}

export async function selectGroup(el, fieldName) {
    const select = findItem(el, `.o_add_custom_group_menu .o_dropdown_menu select`);
    select.value = fieldName;
    await triggerEvent(select, null, "change");
}

export async function applyGroup(el) {
    await click(findItem(el, `.o_add_custom_group_menu .o_dropdown_menu button`));
}

/** Favorite menu */

export async function toggleFavoriteMenu(el) {
    await click(findItem(el, `.o_favorite_menu .o_dropdown_toggler`));
}

export async function deleteFavorite(el, favoriteFinder) {
    const favorite = findItem(el, `.o_favorite_menu .o_menu_item`, favoriteFinder);
    await click(findItem(favorite, "i.fa-trash-o"));
}

export async function toggleSaveFavorite(el) {
    await click(findItem(el, `.o_favorite_menu .o_add_favorite .o_dropdown_toggler`));
}

export async function editFavoriteName(el, name) {
    const input = findItem(
        el,
        `.o_favorite_menu .o_add_favorite .o_dropdown_menu input[type="text"]`
    );
    input.value = name;
    await triggerEvent(input, null, "input");
}

export async function saveFavorite(el) {
    await click(findItem(el, `.o_favorite_menu .o_add_favorite .o_dropdown_menu button`));
}

/** Comparison menu */

export async function toggleComparisonMenu(el) {
    await click(findItem(el, `.o_comparison_menu button.o_dropdown_toggler`));
}

/** Search bar */

export function getFacetTexts(target) {
    const el = getNode(target);
    return [...el.querySelectorAll(`div.o_searchview_facet`)].map((facet) =>
        facet.innerText.trim()
    );
}

export async function removeFacet(el, facetFinder = 0) {
    const facet = findItem(el, `div.o_searchview_facet`, facetFinder);
    await click(facet.querySelector("i.o_facet_remove"));
}

export async function editSearch(el, value) {
    const input = findItem(el, `.o_searchview input`);
    input.value = value;
    await triggerEvent(input, null, "input");
}

export async function validateSearch(el) {
    const input = findItem(el, `.o_searchview input`);
    await triggerEvent(input, null, "keydown", { key: "Enter" });
}

/** Switch View */

export async function switchView(el, viewType) {
    await click(findItem(el, `button.o_switch_view.o_${viewType}`));
}

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
