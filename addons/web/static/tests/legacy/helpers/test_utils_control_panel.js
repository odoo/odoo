/** @odoo-module **/
    
    import { click, findItem, getNode, triggerEvent } from "./test_utils_dom";
    import { editInput, editSelect, editAndTrigger } from "./test_utils_fields";

    //-------------------------------------------------------------------------
    // Exported functions
    //-------------------------------------------------------------------------

    /**
     * @param {EventTarget} el
     * @param {(number|string)} menuFinder
     * @returns {Promise}
     */
    export async function toggleMenu(el, menuFinder) {
        const menu = findItem(el, `.dropdown > button`, menuFinder);
        await click(menu);
    }

    /**
     * @param {EventTarget} el
     * @param {(number|string)} itemFinder
     * @returns {Promise}
     */
    export async function toggleMenuItem(el, itemFinder) {
        const item = findItem(el, `.o_menu_item > a`, itemFinder);
        await click(item);
    }

    /**
     * @param {EventTarget} el
     * @param {(number|string)} itemFinder
     * @param {(number|string)} optionFinder
     * @returns {Promise}
     */
    export async function toggleMenuItemOption(el, itemFinder, optionFinder) {
        const item = findItem(el, `.o_menu_item > a`, itemFinder);
        const option = findItem(item.parentNode, '.o_item_option > a', optionFinder);
        await click(option);
    }

    /**
     * @param {EventTarget} el
     * @param {(number|string)} itemFinder
     * @returns {boolean}
     */
    export function isItemSelected(el, itemFinder) {
        const item = findItem(el, `.o_menu_item > a`, itemFinder);
        return item.classList.contains('selected');
    }

    /**
     * @param {EventTarget} el
     * @param {(number|string)} itemuFinder
     * @param {(number|string)} optionFinder
     * @returns {boolean}
     */
    export function isOptionSelected(el, itemFinder, optionFinder) {
        const item = findItem(el, `.o_menu_item > a`, itemFinder);
        const option = findItem(item.parentNode, '.o_item_option > a', optionFinder);
        return option.classList.contains('selected');
    }

    /**
     * @param {EventTarget} el
     * @returns {string[]}
     */
    export function getMenuItemTexts(el) {
        return [...getNode(el).querySelectorAll(`.dropdown ul .o_menu_item`)].map(
            e => e.innerText.trim()
        );
    }

    /**
     * @param {EventTarget} el
     * @returns {HTMLButtonElement[]}
     */
    export function getButtons(el) {
        return [...getNode(el).querySelector((`div.o_cp_bottom div.o_cp_buttons`)).children];
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function toggleFilterMenu(el) {
        await click(getNode(el).querySelector(`.o_filter_menu button`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function toggleAddCustomFilter(el) {
        await click(getNode(el).querySelector(`button.o_add_custom_filter`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function applyFilter(el) {
        await click(getNode(el).querySelector(`div.o_add_filter_menu > button.o_apply_filter`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function addCondition(el) {
        await click(getNode(el).querySelector(`div.o_add_filter_menu > button.o_add_condition`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function toggleGroupByMenu(el) {
        await click(getNode(el).querySelector(`.o_group_by_menu button`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function toggleAddCustomGroup(el) {
        await click(getNode(el).querySelector(`span.o_add_custom_group_by`));
    }

    /**
     * @param {EventTarget} el
     * @param {string} fieldName
     * @returns {Promise}
     */
    export async function selectGroup(el, fieldName) {
        await editSelect(
            getNode(el).querySelector(`select.o_group_by_selector`),
            fieldName
        );
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function applyGroup(el) {
        await click(getNode(el).querySelector(`div.o_add_group_by_menu > button.o_apply_group_by`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function toggleFavoriteMenu(el) {
        await click(getNode(el).querySelector(`.o_favorite_menu button`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function toggleSaveFavorite(el) {
        await click(getNode(el).querySelector(`.o_favorite_menu .o_add_favorite .dropdown-item`));
    }

    /**
     * @param {EventTarget} el
     * @param {string} name
     * @returns {Promise}
     */
    export async function editFavoriteName(el, name) {
        await editInput(getNode(el).querySelector(`.o_favorite_menu .o_add_favorite input[type="text"]`), name);
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function saveFavorite(el) {
        await click(getNode(el).querySelector(`.o_favorite_menu .o_add_favorite button.o_save_favorite`));
    }

    /**
     * @param {EventTarget} el
     * @param {(string|number)} favoriteFinder
     * @returns {Promise}
     */
    export async function deleteFavorite(el, favoriteFinder) {
        const favorite = findItem(el, `.o_favorite_menu .o_menu_item`, favoriteFinder);
        await click(favorite.querySelector('i.fa-trash'));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function toggleComparisonMenu(el) {
        await click(getNode(el).querySelector(`div.o_comparison_menu > button`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export function getFacetTexts(el) {
        return [...getNode(el).querySelectorAll(`.o_searchview .o_searchview_facet`)].map(
            facet => facet.innerText.trim()
        );
    }

    /**
     * @param {EventTarget} el
     * @param {(string|number)} facetFinder
     * @returns {Promise}
     */
    export async function removeFacet(el, facetFinder = 0) {
        const facet = findItem(el, `.o_searchview .o_searchview_facet`, facetFinder);
        await click(facet.querySelector('.o_facet_remove'));
    }

    /**
     * @param {EventTarget} el
     * @param {string} value
     * @returns {Promise}
     */
    export async function editSearch(el, value) {
        await editInput(getNode(el).querySelector(`.o_searchview_input`), value);
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function validateSearch(el) {
        await triggerEvent(
            getNode(el).querySelector(`.o_searchview_input`),
            'keydown', { key: 'Enter' }
        );
    }

    /**
     * @param {EventTarget} el
     * @param {string} [menuFinder="Action"]
     * @returns {Promise}
     */
    export async function toggleActionMenu(el, menuFinder = "Action") {
        const dropdown = findItem(el, `.o_cp_action_menus button`, menuFinder);
        await click(dropdown);
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function pagerPrevious(el) {
        await click(getNode(el).querySelector(`.o_pager button.o_pager_previous`));
    }

    /**
     * @param {EventTarget} el
     * @returns {Promise}
     */
    export async function pagerNext(el) {
        await click(getNode(el).querySelector(`.o_pager button.o_pager_next`));
    }

    /**
     * @param {EventTarget} el
     * @returns {string}
     */
    export function getPagerValue(el) {
        const pagerValue = getNode(el).querySelector(`.o_pager_counter .o_pager_value`);
        switch (pagerValue.tagName) {
            case 'INPUT':
                return pagerValue.value;
            case 'SPAN':
                return pagerValue.innerText.trim();
        }
    }

    /**
     * @param {EventTarget} el
     * @returns {string}
     */
    export function getPagerSize(el) {
        return getNode(el).querySelector(`.o_pager_counter span.o_pager_limit`).innerText.trim();
    }

    /**
     * @param {EventTarget} el
     * @param {string} value
     * @returns {Promise}
     */
    export async function setPagerValue(el, value) {
        let pagerValue = getNode(el).querySelector(`.o_pager_counter .o_pager_value`);
        if (pagerValue.tagName === 'SPAN') {
            await click(pagerValue);
        }
        pagerValue = getNode(el).querySelector(`.o_pager_counter input.o_pager_value`);
        if (!pagerValue) {
            throw new Error("Pager value is being edited and cannot be changed.");
        }
        await editAndTrigger(pagerValue, value, ['change', 'blur']);
    }

    /**
     * @param {EventTarget} el
     * @param {string} viewType
     * @returns {Promise}
     */
    export async function switchView(el, viewType) {
        await click(getNode(el).querySelector(`button.o_switch_view.o_${viewType}`));
    }
