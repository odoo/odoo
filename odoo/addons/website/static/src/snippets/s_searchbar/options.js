/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import options from '@web_editor/js/editor/snippets.options';

options.registry.SearchBar = options.Class.extend({
    /**
     * @override
     */
    start() {
        this.searchInputEl = this.$target[0].querySelector(".oe_search_box");
        this.searchButtonEl = this.$target[0].querySelector(".oe_search_button");
        return this._super(...arguments);
    },
    /**
     * @override
     */
    onBuilt() {
        // Fix in stable to remove the hard-coded "Light" style from the search
        // bar and allow the search bar to adopt the styles of the theme's
        // inputs. An option "setSearchbarStyle" has also been added to enable
        // users to set the "Light" style if desired.
        if (!this.$target[0].closest(".s_custom_snippet")) {
            this._setSearchbarStyleLight(false);
        }
    },

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    setSearchType: function (previewMode, widgetValue, params) {
        const form = this.$target.parents('form');
        form.attr('action', params.formAction);

        if (!previewMode) {
            this.trigger_up('snippet_edition_request', {exec: () => {
                const widget = this._requestUserValueWidgets('order_opt')[0];
                const orderBy = widget.getValue("selectDataAttribute");
                const order = widget.$el.find("we-button[data-select-data-attribute='" + orderBy + "']")[0];
                if (order.classList.contains("d-none")) {
                    const defaultOrder = widget.$el.find("we-button[data-name='order_name_asc_opt']")[0];
                    defaultOrder.click(); // open
                    defaultOrder.click(); // close
                }
            }});

            // Reset display options.
            const displayOptions = new Set();
            for (const optionEl of this.$el[0].querySelectorAll('[data-dependencies="limit_opt"] [data-attribute-name^="display"]')) {
                displayOptions.add(optionEl.dataset.attributeName);
            }
            const scopeName = this.$el[0].querySelector(`[data-set-search-type="${widgetValue}"]`).dataset.name;
            for (const displayOption of displayOptions) {
                this.$target[0].dataset[displayOption] = this.$el[0].querySelector(
                    `[data-attribute-name="${displayOption}"][data-dependencies="${scopeName}"]`
                ) ? 'true' : '';
            }
        }
    },

    setOrderBy: function (previewMode, widgetValue, params) {
        const form = this.$target.parents('form');
        form.find(".o_search_order_by").attr("value", widgetValue);
    },
    /**
     * Sets the style of the searchbar.
     *
     * @see this.selectClass for parameters
     */
    setSearchbarStyle(previewMode, widgetValue, params) {
        this._setSearchbarStyleLight(widgetValue === "light");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState(methodName, params) {
        if (methodName === "setSearchbarStyle") {
            const searchInputIsLight = this.searchInputEl.matches(".border-0.bg-light");
            const searchButtonIsLight = this.searchButtonEl.matches(".btn-light");
            return searchInputIsLight && searchButtonIsLight ? "light" : "default";
        }
        return this._super(...arguments);
    },
    /**
     * @todo Adapt in the XML directly in master.
     * @override
     */
    async _renderCustomXML(uiFragment) {
        // Create the <we-select> for the "Style" option, with choices "Default
        // Input Style" and "Light". This is a stable fix to allow the user to
        // apply the input style defined in the theme options to the search bar.
        // Previously, the search bar style was hardcoded with the "Light"
        // style, which was not visible with the default "Light" background of
        // the "Search" snippet. Allowing the search bar to have the same style
        // as the other inputs is also more coherent.
        const weSelectEl = document.createElement("we-select");
        weSelectEl.setAttribute("string", _t("Style"));
        const defaultBtnEl = document.createElement("we-button");
        defaultBtnEl.dataset.setSearchbarStyle = "default";
        defaultBtnEl.textContent = _t("Default Input Style");
        const lightBtnEl = document.createElement("we-button");
        lightBtnEl.dataset.setSearchbarStyle = "light";
        lightBtnEl.textContent = _t("Light");
        weSelectEl.appendChild(defaultBtnEl);
        weSelectEl.appendChild(lightBtnEl);

        uiFragment.appendChild(weSelectEl);
    },
    /**
     * @private
     * @param {boolean} light
     */
    _setSearchbarStyleLight(light) {
        this.searchInputEl.classList.toggle("border-0", light);
        this.searchInputEl.classList.toggle("bg-light", light);
        this.searchButtonEl.classList.toggle("btn-light", light);
        this.searchButtonEl.classList.toggle("btn-primary", !light);
    },
});

export default {
    SearchBar: options.registry.SearchBar,
};
