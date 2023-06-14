/** @odoo-module **/

import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import {
    click,
    editInput,
    getFixture,
    mount,
    mouseEnter,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { CustomFavoriteItem } from "@web/search/favorite_menu/custom_favorite_item";
import { WithSearch } from "@web/search/with_search/with_search";
import { getDefaultConfig } from "@web/views/view";
import { viewService } from "@web/views/view_service";
import { actionService } from "@web/webclient/actions/action_service";
import { dialogService } from "@web/core/dialog/dialog_service";
import { MainComponentsContainer } from "@web/core/main_components_container";

import { Component, xml } from "@odoo/owl";
const serviceRegistry = registry.category("services");
const favoriteMenuRegistry = registry.category("favoriteMenu");

export function setupControlPanelServiceRegistry() {
    serviceRegistry.add("action", actionService);
    serviceRegistry.add("hotkey", hotkeyService);
    serviceRegistry.add("notification", notificationService);
    serviceRegistry.add("orm", ormService);
    serviceRegistry.add("view", viewService);
    serviceRegistry.add("dialog", dialogService);
}

export function setupControlPanelFavoriteMenuRegistry() {
    favoriteMenuRegistry.add(
        "custom-favorite-item",
        { Component: CustomFavoriteItem, groupNumber: 3 },
        { sequence: 0 }
    );
}

export async function makeWithSearch(params) {
    const props = { ...params };

    const serverData = props.serverData || undefined;
    const mockRPC = props.mockRPC || undefined;
    const config = {
        ...getDefaultConfig(),
        ...props.config,
    };

    delete props.serverData;
    delete props.mockRPC;
    delete props.config;
    const componentProps = props.componentProps || {};
    delete props.componentProps;
    delete props.Component;

    class Parent extends Component {
        setup() {
            this.withSearchProps = props;
            this.componentProps = componentProps;
        }
        getDisplay(display) {
            return Object.assign({}, display, componentProps.display);
        }
    }
    Parent.template = xml`
        <WithSearch t-props="withSearchProps" t-slot-scope="search">
            <Component
                t-props="componentProps"
                context="search.context"
                domain="search.domain"
                groupBy="search.groupBy"
                orderBy="search.orderBy"
                comparison="search.comparison"
                display="getDisplay(search.display)"/>
        </WithSearch>
        <MainComponentsContainer />
    `;
    Parent.components = { Component: params.Component, WithSearch, MainComponentsContainer };

    const env = await makeTestEnv({ serverData, mockRPC });
    const searchEnv = Object.assign(Object.create(env), { config });
    const parent = await mount(Parent, getFixture(), { env: searchEnv, props });
    const parentNode = parent.__owl__;
    const withSearchNode = getUniqueChild(parentNode);
    const componentNode = getUniqueChild(withSearchNode);
    const component = componentNode.component;
    return component;
}

function getUniqueChild(node) {
    return Object.values(node.children)[0];
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
    return elems.find((el) => el.innerText.trim().toLowerCase() === String(finder).toLowerCase());
}

/** Menu (generic) */

export async function toggleMenu(el, menuFinder) {
    const menu = findItem(el, `.dropdown button.dropdown-toggle`, menuFinder);
    await click(menu);
}

export async function toggleMenuItem(el, itemFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    if (item.classList.contains("dropdown-toggle")) {
        await mouseEnter(item);
    } else {
        await click(item);
    }
}

export async function toggleMenuItemOption(el, itemFinder, optionFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    const option = findItem(item.parentNode, ".o_item_option", optionFinder);
    if (option.classList.contains("dropdown-toggle")) {
        await mouseEnter(option);
    } else {
        await click(option);
    }
}

export function isItemSelected(el, itemFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    return item.classList.contains("selected");
}

export function isOptionSelected(el, itemFinder, optionFinder) {
    const item = findItem(el, `.o_menu_item`, itemFinder);
    const option = findItem(item.parentNode, ".o_item_option", optionFinder);
    return option.classList.contains("selected");
}

export function getMenuItemTexts(target) {
    const el = getNode(target);
    return [...el.querySelectorAll(`.dropdown-menu .o_menu_item`)].map((e) => e.innerText.trim());
}

export function getButtons(el) {
    return [...el.querySelector(`div.o_cp_bottom div.o_cp_buttons`).children];
}

/** Filter menu */

export async function toggleFilterMenu(el) {
    await click(findItem(el, `.o_filter_menu button.dropdown-toggle`));
}

export async function toggleAddCustomFilter(el) {
    await mouseEnter(findItem(el, `.o_add_custom_filter_menu .dropdown-toggle`));
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

export async function editConditionValue(el, index, value, valueIndex = 0) {
    const condition = findItem(el, `.o_filter_condition`, index);
    const target = findItem(
        condition,
        ".o_generator_menu_value input:not([type=hidden]),.o_generator_menu_value select",
        valueIndex
    );
    target.value = value;
    await triggerEvent(target, null, "change");
}

export async function applyFilter(el) {
    await click(findItem(el, `.o_add_custom_filter_menu .dropdown-menu button.o_apply_filter`));
}

export async function addCondition(el) {
    await click(findItem(el, `.o_add_custom_filter_menu .dropdown-menu button.o_add_condition`));
}

export async function removeCondition(el, index) {
    const condition = findItem(el, `.o_filter_condition`, index);
    await click(findItem(condition, ".o_generator_menu_delete"));
}

/** Group by menu */

export async function toggleGroupByMenu(el) {
    await click(findItem(el, `.o_group_by_menu .dropdown-toggle`));
}

export async function toggleAddCustomGroup(el) {
    await mouseEnter(findItem(el, `.o_add_custom_group_menu .dropdown-toggle`));
}

export async function selectGroup(el, fieldName) {
    const select = findItem(el, `.o_add_custom_group_menu .dropdown-menu select`);
    select.value = fieldName;
    await triggerEvent(select, null, "change");
}

export async function applyGroup(el) {
    await click(findItem(el, `.o_add_custom_group_menu .dropdown-menu .btn`));
}

export async function groupByMenu(el, fieldName) {
    await toggleGroupByMenu(el);
    await toggleAddCustomGroup(el);
    await selectGroup(el, fieldName);
    await applyGroup(el);
}

/** Favorite menu */

export async function toggleFavoriteMenu(el) {
    await click(findItem(el, `.o_favorite_menu .dropdown-toggle`));
}

export async function deleteFavorite(el, favoriteFinder) {
    const favorite = findItem(el, `.o_favorite_menu .o_menu_item`, favoriteFinder);
    await click(findItem(favorite, "i.fa-trash-o"));
}

export async function toggleSaveFavorite(el) {
    await mouseEnter(findItem(el, `.o_favorite_menu .o_add_favorite .dropdown-toggle`));
}

export async function editFavoriteName(el, name) {
    const input = findItem(
        el,
        `.o_favorite_menu .o_add_favorite .dropdown-menu input[type="text"]`
    );
    input.value = name;
    await triggerEvent(input, null, "input");
}

export async function saveFavorite(el) {
    await click(findItem(el, `.o_favorite_menu .o_add_favorite .dropdown-menu button`));
}

/** Comparison menu */

export async function toggleComparisonMenu(el) {
    await click(findItem(el, `.o_comparison_menu button.dropdown-toggle`));
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

/** Pager */

export function getPagerValue(el) {
    const valueEl = findItem(el, ".o_pager .o_pager_value");
    return valueEl.innerText.trim().split("-").map(Number);
}

export function getPagerLimit(el) {
    const limitEl = findItem(el, ".o_pager .o_pager_limit");
    return Number(limitEl.innerText.trim());
}

export async function pagerNext(el) {
    await click(findItem(el, ".o_pager button.o_pager_next"));
}

export async function pagerPrevious(el) {
    await click(findItem(el, ".o_pager button.o_pager_previous"));
}

export async function editPager(el, value) {
    await click(findItem(el, ".o_pager .o_pager_value"));
    await editInput(getNode(el), ".o_pager .o_pager_value.o_input", value);
}

/////////////////////////////////////
// Action Menu
/////////////////////////////////////
/**
 * @param {EventTarget} el
 * @param {string} [menuFinder="Action"]
 * @returns {Promise}
 */
export async function toggleActionMenu(el, menuFinder = "Action") {
    const dropdown = findItem(el, `.o_cp_action_menus button`, menuFinder);
    await click(dropdown);
}
