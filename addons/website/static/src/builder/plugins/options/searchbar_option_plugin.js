import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchbarOption } from "./searchbar_option";
import { BuilderAction } from "@html_builder/core/builder_action";

class SearchbarOptionPlugin extends Plugin {
    static id = "searchbarOption";
    resources = {
        builder_options: [SearchbarOption],
        builder_actions: {
            SetSearchTypeAction,
            SetOrderByAction,
            SetSearchbarStyleAction,
            // This resets the data attribute to an empty string on clean.
            // TODO: modify the Python `_search_get_detail()` (grep
            // `with_description = options['displayDescription']`) so we can use
            // the default `dataAttributeAction`. The python should not need a
            // value if it doesn't exist.
            SetNonEmptyDataAttributeAction,
        },
        so_content_addition_selector: [".s_searchbar_input"],
        searchbar_option_order_by_items: {
            label: _t("Name (A-Z)"),
            orderBy: "name asc",
            id: "order_name_asc_opt",
        },
        searchbar_option_display_items: [
            {
                label: _t("Description"),
                dataAttribute: "displayDescription",
                dependency: "search_all_opt",
            },
            {
                label: _t("Content"),
                dataAttribute: "displayDescription",
                dependency: "search_pages_opt",
            },
            {
                label: _t("Extra Link"),
                dataAttribute: "displayExtraLink",
                dependency: "search_all_opt",
            },
            {
                label: _t("Detail"),
                dataAttribute: "displayDetail",
                dependency: "search_all_opt",
            },
            {
                label: _t("Image"),
                dataAttribute: "displayImage",
                dependency: "search_all_opt",
            },
        ],
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

        // Reset display options. Has to be done in 2 steps, because
        // the same option may be on 2 dependencies, and we don't
        // want the 1st to add it and the 2nd to delete it.
        const displayDataAttributes = new Set();
        for (const item of this.getResource("searchbar_option_display_items")) {
            if (isDependencyActive(item.dependency)) {
                displayDataAttributes.add(item.dataAttribute);
            } else {
                delete editingElement.dataset[item.dataAttribute];
            }
        }
        for (const dataAttribute of displayDataAttributes) {
            editingElement.dataset[dataAttribute] = "true";
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
// This resets the data attribute to an empty string on clean.
// TODO: modify the Python `_search_get_detail()` (grep
// `with_description = options['displayDescription']`) so we can use
// the default `dataAttributeAction`. The python should not need a
// value if it doesn't exist.
export class SetNonEmptyDataAttributeAction extends BuilderAction {
    static id = "setNonEmptyDataAttribute";
    getValue({ editingElement, params: { mainParam: attributeName } = {} }) {
        return editingElement.dataset[attributeName];
    }
    isApplied({ editingElement, params: { mainParam: attributeName } = {}, value = "" }) {
        return editingElement.dataset[attributeName] === value;
    }
    apply({ editingElement, params: { mainParam: attributeName } = {}, value }) {
        if (value) {
            editingElement.dataset[attributeName] = value;
        } else {
            delete editingElement.dataset[attributeName];
        }
    }
    clean({ editingElement, params: { mainParam: attributeName } = {} }) {
        editingElement.dataset[attributeName] = "";
    }
}

registry.category("website-plugins").add(SearchbarOptionPlugin.id, SearchbarOptionPlugin);
