import { SnippetOption } from "@web_editor/js/editor/snippets.options";
import { registerContentAdditionSelector } from "@web_editor/js/editor/snippets.registry";
import { registerWebsiteOption } from "@website/js/editor/snippets.registry";

export class SearchBar extends SnippetOption {
    constructor({ callbacks }) {
        super(...arguments);
        this.requestUserValue = callbacks.requestUserValue;
        this._constructor();
    }

    /**
     * Allows patching the constructor.
     *
     * @protected
     */
    _constructor() {
    }

    /**
     * @override
     */
    async willStart() {
        await super.willStart(...arguments);
        this.searchInputEl = this.$target[0].querySelector(".oe_search_box");
        this.searchButtonEl = this.$target[0].querySelector(".oe_search_button");
    }

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    setSearchType(previewMode, widgetValue, params) {
        const form = this.$target.parents('form');
        form.attr('action', params.formAction);

        if (!previewMode) {
            this.env.snippetEditionRequest(async () => {
                // Reset orderBy if current value is not present in searchType
                const orderBySelect = this.requestUserValue({ name: "order_opt" });
                const currentOrderBy = orderBySelect.getValue("selectDataAttribute");
                const currentOrderByButton = Object.values(orderBySelect._subValues)
                    .find(userValue => userValue._data.selectDataAttribute === currentOrderBy);
                if (!currentOrderByButton.show) {
                    const defaultOrderByWidget = orderBySelect.findWidget("order_name_asc_opt");
                    defaultOrderByWidget.enable();
                }

                // Reset display options.
                const displayOptions = Object.values(this._userValues)
                    .filter(userValue => userValue._data.attributeName?.startsWith("display"));
                const displayOptionsNames = new Set(
                    displayOptions.map(userValue => userValue._data.attributeName)
                );
                const shownDisplayOptions = displayOptions.filter(userValue => userValue.show);
                for (const displayOptionName of displayOptionsNames) {
                    const shownUserValue = shownDisplayOptions.find(
                        userValue => userValue._data.attributeName === displayOptionName
                    );
                    const isEnabled = !!shownUserValue;
                    this.$target[0].dataset[displayOptionName] = isEnabled ? "true" : "";

                    if (shownUserValue) {
                        // TODO: @owl-options Should this be needed ?
                        await shownUserValue.setValue("true");
                    }
                }
            });
        }
    }
    setOrderBy(previewMode, widgetValue, params) {
        const form = this.$target.parents('form');
        form.find(".o_search_order_by").attr("value", widgetValue);
    }
    /**
     * Sets the style of the searchbar.
     *
     * @see this.selectClass for parameters
     */
    setSearchbarStyle(previewMode, widgetValue, params) {
        const isLight = (widgetValue === "light");
        this.searchInputEl.classList.toggle("border-0", isLight);
        this.searchInputEl.classList.toggle("bg-light", isLight);
        this.searchButtonEl.classList.toggle("btn-light", isLight);
        this.searchButtonEl.classList.toggle("btn-primary", !isLight);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async _computeWidgetState(methodName, params) {
        if (methodName === "setSearchbarStyle") {
            const searchInputIsLight = this.searchInputEl.matches(".border-0.bg-light");
            const searchButtonIsLight = this.searchButtonEl.matches(".btn-light");
            return searchInputIsLight && searchButtonIsLight ? "light" : "default";
        }
        return super._computeWidgetState(...arguments);
    }
}

registerWebsiteOption("SearchBar", {
    Class: SearchBar,
    template: "website.s_searchbar_options",
    selector: ".s_searchbar_input",
});
registerContentAdditionSelector(".s_searchbar_input");
