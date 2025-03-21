import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchbarOption } from "./searchbar_option";

class SearchbarOptionPlugin extends Plugin {
    static id = "searchbarOption";
    resources = {
        builder_options: [
            {
                OptionComponent: SearchbarOption,
                selector: ".s_searchbar_input",
                applyTo: ".search-query",
                props: {
                    getOrderByItems: () => this.getResource("searchbar_option_order_by_items"),
                    getDisplayItems: () => this.getResource("searchbar_option_display_items"),
                },
            },
        ],
        builder_actions: this.getActions(),
        searchbar_option_order_by_items: {
            label: _t("Name (A-Z)"),
            orderBy: "name asc",
            id: "order_name_asc_opt",
        },
        searchbar_option_display_items: [
            {
                label: _t("Description"),
                dataAttributeAction: "displayDescription",
                dependency: "search_all_opt",
            },
            {
                label: _t("Content"),
                dataAttributeAction: "displayDescription",
                dependency: "search_pages_opt",
            },
            {
                label: _t("Extra Link"),
                dataAttributeAction: "displayExtraLink",
                dependency: "search_all_opt",
            },
            {
                label: _t("Detail"),
                dataAttributeAction: "displayDetail",
                dependency: "search_all_opt",
            },
            {
                label: _t("Image"),
                dataAttributeAction: "displayImage",
                dependency: "search_all_opt",
            },
        ],
    };
    defaultSearchType = "name asc";

    getFormEl(editingElement) {
        return editingElement.closest("form");
    }
    getSearchButtonEl(editingElement) {
        return editingElement.closest(".s_searchbar_input").querySelector(".oe_search_button");
    }
    getSearchOrderByInputEl(editingElement) {
        return this.getFormEl(editingElement).querySelector(".o_search_order_by");
    }

    getActions() {
        return {
            setSearchType: {
                apply: ({ editingElement, value: formAction, dependencyManager }) => {
                    this.getFormEl(editingElement).action = formAction;

                    const isDependencyActive = (dep) =>
                        !dep || dependencyManager.get(dep).isActive();

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
                    const displayDataAttributeActions = new Set();
                    for (const item of this.getResource("searchbar_option_display_items")) {
                        if (isDependencyActive(item.dependency)) {
                            displayDataAttributeActions.add(item.dataAttributeAction);
                        } else {
                            delete editingElement.dataset[item.dataAttributeAction];
                        }
                    }
                    for (const dataAttributeAction of displayDataAttributeActions) {
                        editingElement.dataset[dataAttributeAction] = "true";
                    }
                },
            },
            setOrderBy: {
                apply: ({ editingElement, value: orderBy }) => {
                    this.getSearchOrderByInputEl(editingElement).value = orderBy;
                },
            },
            setSearchbarStyle: {
                isApplied: ({ editingElement, param: { mainParam: style } }) => {
                    const searchInputIsLight = editingElement.matches(".border-0.bg-light");
                    const searchButtonIsLight =
                        this.getSearchButtonEl(editingElement).matches(".btn-light");

                    if (style === "light") {
                        return searchInputIsLight && searchButtonIsLight;
                    }
                    if (style === "default") {
                        return !searchInputIsLight && !searchButtonIsLight;
                    }
                },
                apply: ({ editingElement, param: { mainParam: style } }) => {
                    const isLight = style === "light";
                    const searchButtonEl = this.getSearchButtonEl(editingElement);
                    editingElement.classList.toggle("border-0", isLight);
                    editingElement.classList.toggle("bg-light", isLight);
                    searchButtonEl.classList.toggle("btn-light", isLight);
                    searchButtonEl.classList.toggle("btn-primary", !isLight);
                },
            },
        };
    }
}

registry.category("website-plugins").add(SearchbarOptionPlugin.id, SearchbarOptionPlugin);
