// @ts-check
/** @odoo-module native */

import { Component, onWillDestroy, onWillStart, useState } from "@odoo/owl";
import { AccordionItem } from "@web/components/dropdown/accordion_item";
import { CheckboxItem } from "@web/components/dropdown/checkbox_item";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { useAction } from "@web/core/action_port";
import { isActivationKey } from "@web/core/browser/hotkeys";
import { makeLogger } from "@web/core/debug/debug_logger";
import { SearchModelEvent } from "@web/core/events";
import { registry } from "@web/core/registry";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { useBus } from "@web/core/utils/hooks";
import { CustomGroupByItem } from "@web/search/custom_group_by_item/custom_group_by_item";
/** @import { EnrichedSearchItem } from "@web/search/search_types" */
import { PropertiesGroupByItem } from "@web/search/properties_group_by_item/properties_group_by_item";
import {
    editFavoriteFilter,
    FACET_ICONS,
    getDisplayedRegistryItems,
    groupableFields,
    isGroupableField,
    MENU_REGISTRY_VALIDATION,
} from "@web/search/utils/misc";

const log = makeLogger("web.search.menu");

const favoriteMenuRegistry = registry.category("favoriteMenu");

favoriteMenuRegistry.addValidation(MENU_REGISTRY_VALIDATION);

export class SearchBarMenu extends Component {
    /** @type {import("@web/core/action_port").ActionPort} */
    actionService;

    static template = "web.SearchBarMenu";
    static components = {
        Dropdown,
        DropdownItem,
        CheckboxItem,
        CustomGroupByItem,
        AccordionItem,
        PropertiesGroupByItem,
    };
    static props = {
        slots: {
            type: Object,
            optional: true,
            shape: {
                default: { optional: true },
            },
        },
        dropdownState: { ...Dropdown.props.state },
    };

    /** @type {{Component: Function, groupNumber: number, key: string}[]} */
    otherItems = [];

    /** @type {{ sharedFavoritesExpanded: boolean }} */
    state;

    setup() {
        this.facet_icons = FACET_ICONS;
        this.actionService = useAction();
        this.state = useState({ sharedFavoritesExpanded: false });
        const keepLast = new KeepLast({ rejectSuperseded: true });
        const refreshRegistryItems = async () => {
            let generation;
            try {
                const pending = keepLast.add(this._registryItems());
                generation = keepLast.generation;
                const items = await pending;
                if (generation !== keepLast.generation) {
                    log.logic("visibility-continuation-superseded");
                    return;
                }
                this.otherItems = items;
            } catch (error) {
                if (
                    error instanceof SupersededError ||
                    (generation !== undefined && generation !== keepLast.generation)
                ) {
                    log.logic("visibility-superseded");
                    return;
                }
                throw error;
            }
            log.logic("visibility-applied", () => ({ count: this.otherItems.length }));
            this.render();
        };
        onWillStart(refreshRegistryItems);
        onWillDestroy(() => keepLast.cancel());
        // the registry predicates read the search model, not this component's
        // props (a parent's slot object is new on every render), so they are
        // re-asked when the model changes and not per keystroke in the bar
        useBus(this.env.searchModel, SearchModelEvent.UPDATE, refreshRegistryItems);
    }

    /** @returns {Promise<{Component: Function, groupNumber: number, key: string}[]>} */
    _registryItems() {
        return getDisplayedRegistryItems(
            favoriteMenuRegistry,
            /** @type {import("@web/env").OdooEnv} */ (this.env),
        );
    }

    /** @returns {Object[]} */
    get fields() {
        return groupableFields(this.env.searchModel.searchViewFields, (name, field) =>
            this.isGroupableField(name, field),
        );
    }

    /** @returns {Object[]} */
    get filterItems() {
        return this.env.searchModel.getSearchItems(
            (/** @type {EnrichedSearchItem} */ searchItem) =>
                ["filter", "dateFilter"].includes(searchItem.type),
        );
    }

    async onAddCustomFilterClick() {
        this.env.searchModel.spawnCustomFilterDialog();
    }

    /**
     * @param {object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onFilterSelected({ itemId, optionId }) {
        if (optionId) {
            this.env.searchModel.toggleDateFilter(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }

    /** @returns {boolean} */
    get hideCustomGroupBy() {
        return this.env.searchModel.hideCustomGroupBy || false;
    }

    /** @returns {Object[]} */
    get groupByItems() {
        return this.env.searchModel.getSearchItems(
            (/** @type {EnrichedSearchItem} */ searchItem) =>
                ["groupBy", "dateGroupBy"].includes(searchItem.type) &&
                !(/** @type {any} */ (searchItem).isProperty),
        );
    }

    /**
     * @param {string} fieldName
     * @param {Object} field
     * @returns {boolean}
     */
    isGroupableField(fieldName, field) {
        return isGroupableField(fieldName, field);
    }

    /**
     * @param {object} param0
     * @param {number} param0.itemId
     * @param {number} [param0.optionId]
     */
    onGroupBySelected({ itemId, optionId }) {
        if (optionId) {
            this.env.searchModel.toggleDateGroupBy(itemId, optionId);
        } else {
            this.env.searchModel.toggleSearchItem(itemId);
        }
    }

    /** @param {string} fieldName */
    onAddCustomGroup(fieldName) {
        this.env.searchModel.createNewGroupBy(fieldName);
    }

    /** @returns {Object[]} */
    get favorites() {
        return this.env.searchModel.getSearchItems(
            (/** @type {any} */ searchItem) =>
                searchItem.type === "favorite" && searchItem.userIds.length === 1,
        );
    }

    /** @returns {Object[]} */
    get allSharedFavorites() {
        return this.env.searchModel.getSearchItems(
            (/** @type {any} */ searchItem) =>
                searchItem.type === "favorite" && searchItem.userIds.length !== 1,
        );
    }

    /** @returns {Object[]} */
    get sharedFavorites() {
        const sharedFavorites = this.allSharedFavorites;
        const expanded =
            this.state.sharedFavoritesExpanded || sharedFavorites.length <= 4;
        return expanded ? sharedFavorites : sharedFavorites.slice(0, 3);
    }

    /** @param {number} itemId */
    onFavoriteSelected(itemId) {
        this.env.searchModel.toggleSearchItem(itemId);
    }

    /** @param {number} itemId */
    editFavorite(itemId) {
        editFavoriteFilter(
            this.actionService,
            this.env.searchModel.searchItems[itemId].serverSideId,
        );
    }

    /**
     * @param {KeyboardEvent} ev
     * @param {number} itemId
     */
    onEditFavoriteKeydown(ev, itemId) {
        if (!isActivationKey(ev)) {
            return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        this.editFavorite(itemId);
    }
}
