import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchbarOption } from "./searchbar_option";
import { BuilderAction } from "@html_builder/core/builder_action";

/** @typedef {import("plugins").LazyTranslatedString} LazyTranslatedString */

/**
 * @typedef {{
 *      label: LazyTranslatedString;
 *      orderBy: string;
 *      dependency?: string;
 *      id?: string;
 * }[]} searchbar_option_order_by_items
 *
 * Register orderBy options for the website searchbar.
 * `orderBy` takes a string like `record_field_name` + `asc` or `desc`.
 * `dependency` takes an id of another builder option. You can omit it if the
 * orderBy option should always be visible.
 * You can reference `id` if you need the new option to have an id (if another
 * option depends on it being active).
 *
 * Example:
 *
 *      resources: {
 *          searchbar_option_order_by_items: {
 *              label: _t("Date (old to new)"),
 *              orderBy: "published_date asc",
 *              dependency: "search_blogs_opt",
 *          },
 *      };
 */

class SearchbarOptionPlugin extends Plugin {
    static id = "searchbarOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        builder_options: [SearchbarOption],
        builder_actions: {
            SetSearchTypeAction,
            SetOrderByAction,
            SetSearchbarStyleAction,
        },
        so_content_addition_selector: [".s_searchbar_input"],
        searchbar_option_order_by_items: {
            label: _t("Name (A-Z)"),
            orderBy: "name asc",
            id: "order_name_asc_opt",
        },
        // input group should not be contenteditable, while all other children
        // beside the input are contenteditable
        content_not_editable_selectors: [".input-group:has( > input)"],
        content_editable_selectors: [".input-group:has( > input) > *:not(input)"],
    };
}

export class BaseSearchBarAction extends BuilderAction {
    id = "baseSearchBar";
    defaultSearchType = "name asc";

    getFormEl(editingElement) {
        return editingElement.closest("form");
    }
    getSearchButtonEl(editingElement) {
        // /!\ this could return undefined if the button was deleted.
        return editingElement.closest(".s_searchbar_input").querySelector(".oe_search_button");
    }
    getSearchOrderByInputEl(editingElement) {
        return this.getFormEl(editingElement).querySelector(".o_search_order_by");
    }
}
export class SetSearchTypeAction extends BaseSearchBarAction {
    static id = "setSearchType";
    apply({ editingElement, value: formAction, dependencyManager }) {
        this.getFormEl(editingElement).action = formAction;

        const isDependencyActive = (dep) => !dep || dependencyManager.get(dep).isActive();

        // If the selected orderBy option is not available with the
        // new search type, reset to default.
        const searchOrderByInputEl = this.getSearchOrderByInputEl(editingElement);
        if (
            !this.getResource("searchbar_option_order_by_items").some(
                (item) =>
                    isDependencyActive(item.dependency) &&
                    item.orderBy === searchOrderByInputEl.value
            )
        ) {
            editingElement.dataset.orderBy = this.defaultSearchType;
            searchOrderByInputEl.value = this.defaultSearchType;
        }
    }
}
export class SetOrderByAction extends BaseSearchBarAction {
    static id = "setOrderBy";
    apply({ editingElement, value: orderBy }) {
        this.getSearchOrderByInputEl(editingElement).value = orderBy;
    }
}

export class SetSearchbarStyleAction extends BaseSearchBarAction {
    static id = "setSearchbarStyle";
    isApplied({ editingElement, params: { mainParam: style } }) {
        const searchInputIsLight = editingElement.matches(".border-0.bg-light");
        const searchButtonIsLight = this.getSearchButtonEl(editingElement)?.matches(".btn-light");

        if (style === "light") {
            return searchInputIsLight && searchButtonIsLight;
        }
        if (style === "default") {
            return !searchInputIsLight && !searchButtonIsLight;
        }
    }
    apply({ editingElement, params: { mainParam: style } }) {
        const isLight = style === "light";
        const searchButtonEl = this.getSearchButtonEl(editingElement);
        editingElement.classList.toggle("border-0", isLight);
        editingElement.classList.toggle("bg-light", isLight);
        searchButtonEl?.classList.toggle("btn-light", isLight);
        searchButtonEl?.classList.toggle("btn-primary", !isLight);
    }
}

registry.category("website-plugins").add(SearchbarOptionPlugin.id, SearchbarOptionPlugin);
