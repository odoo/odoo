import { queryAll, queryAllTexts, queryOne, queryText } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { findComponent, mountWithCleanup } from "./component_test_helpers";
import { contains } from "./dom_test_helpers";
import { getMockEnv, makeMockEnv } from "./env_test_helpers";

import { WithSearch } from "@web/search/with_search/with_search";
import { getDefaultConfig } from "@web/views/view";

const ensureSearchView = async () => {
    if (
        getMockEnv().isSmall &&
        queryAll`.o_control_panel_navigation`.length &&
        !queryAll`.o_searchview`.length
    ) {
        await contains(`.o_control_panel_navigation button`).click();
    }
};

const ensureSearchBarMenu = async () => {
    if (!queryAll`.o_search_bar_menu`.length) {
        await toggleSearchBarMenu();
    }
};

/**
 * This function is aim to be used only in the tests.
 * It will filter the props that are needed by the Component.
 * This is to avoid errors of props validation. This occurs for example, on ControlPanel tests.
 * In production, View use WithSearch for the Controllers, and the Layout send only the props that
 * need to the ControlPanel.
 *
 * @param {Component} Component
 * @param {Object} props
 * @returns {Object} filtered props
 */
function filterPropsForComponent(Component, props) {
    // This if, can be removed once all the Components have the props defined
    if (Component.props) {
        let componentKeys = null;
        if (Component.props instanceof Array) {
            componentKeys = Component.props.map((x) => x.replace("?", ""));
        } else {
            componentKeys = Object.keys(Component.props);
        }
        if (componentKeys.includes("*")) {
            return props;
        } else {
            return Object.keys(props)
                .filter((k) => componentKeys.includes(k))
                .reduce((o, k) => {
                    o[k] = props[k];
                    return o;
                }, {});
        }
    } else {
        return props;
    }
}

//-----------------------------------------------------------------------------
// Search view
//-----------------------------------------------------------------------------

/**
 * Mounts a component wrapped within a WithSearch.
 *
 * @template T
 * @param {T} componentConstructor
 * @param {Record<string, any>} [options]
 * @param {Record<string, any>} [config]
 * @returns {Promise<InstanceType<T>>}
 */
export async function mountWithSearch(componentConstructor, searchProps = {}, config = {}) {
    class ComponentWithSearch extends Component {
        static template = xml`
            <WithSearch t-props="withSearchProps" t-slot-scope="search">
                <t t-component="component" t-props="getProps(search)"/>
            </WithSearch>
        `;
        static components = { WithSearch };
        static props = ["*"];

        setup() {
            this.withSearchProps = searchProps;
            this.component = componentConstructor;
        }

        getProps(search) {
            const props = {
                context: search.context,
                domain: search.domain,
                groupBy: search.groupBy,
                orderBy: search.orderBy,
                comparison: search.comparison,
                display: search.display,
            };
            return filterPropsForComponent(componentConstructor, props);
        }
    }

    const fullConfig = { ...getDefaultConfig(), ...config };
    const env = await makeMockEnv({ config: fullConfig });
    const root = await mountWithCleanup(ComponentWithSearch, { env });
    return findComponent(root, (component) => component instanceof componentConstructor);
}

//-----------------------------------------------------------------------------
// Menu (generic)
//-----------------------------------------------------------------------------

/**
 * @param {string} label
 */
export async function toggleMenu(label) {
    await contains(`button.o-dropdown:contains(/^${label}$/i)`).click();
}

/**
 * @param {string} label
 */
export async function toggleMenuItem(label) {
    const target = queryOne`.o_menu_item:contains(/^${label}$/i)`;
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
    const { parentElement: root } = queryOne`.o_menu_item:contains(/^${itemLabel}$/i)`;
    const target = queryOne(`.o_item_option:contains(/^${optionLabel}$/i)`, { root });
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
    return queryOne`.o_menu_item:contains(/^${label}$/i)`.classList.contains("selected");
}

/**
 * @param {string} itemLabel
 * @param {string} optionLabel
 */
export function isOptionSelected(itemLabel, optionLabel) {
    const { parentElement: root } = queryOne`.o_menu_item:contains(/^${itemLabel}$/i)`;
    return queryOne(`.o_item_option:contains(/^${optionLabel}$/i)`, { root }).classList.contains(
        "selected"
    );
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
    await contains(`.o_add_custom_group_menu`).select(fieldName);
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
    await contains(`.o_favorite_menu .o_menu_item:contains(/^${text}$/i) i.fa-trash-o`).click();
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
    await contains(`.o_searchview_facet:contains(/^${label}$/i) .o_facet_remove`).click();
}

/**
 * @param {string} value
 */
export async function editSearch(value) {
    await ensureSearchView();
    await contains(`.o_searchview input`).edit(value, { confirm: false });
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

/**
 * @param {HTMLElement} root
 */
export function getPagerValue(root) {
    return queryText(".o_pager .o_pager_value", { root })
        .split(/\s*-\s*/)
        .map(Number);
}

/**
 * @param {HTMLElement} root
 */
export function getPagerLimit(root) {
    return parseInt(queryText(".o_pager .o_pager_limit", { root }), 10);
}

/**
 * @param {HTMLElement} root
 */
export async function pagerNext(root) {
    await contains(".o_pager button.o_pager_next", { root }).click();
}

/**
 * @param {HTMLElement} root
 */
export async function pagerPrevious(root) {
    await contains(".o_pager button.o_pager_previous", { root }).click();
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
