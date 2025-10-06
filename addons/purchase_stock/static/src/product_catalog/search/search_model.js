import { AccountProductCatalogSearchModel } from "@account/components/product_catalog/search/search_model";
import { useSubEnv } from "@odoo/owl";
import { getSuggestToggleState } from "../utils";

export class PurchaseStockProductCatalogSearchModel extends AccountProductCatalogSearchModel {
    setup() {
        super.setup(...arguments);
        this.suggest = {
            numberOfDays: 0,
            basedOn: null,
            percentFactor: 0,
            suggestToggle: { isOn: false },
            totalEstimatedPrice: 0,
        };
        useSubEnv({
            suggest: this.suggest,
            _computeTotalEstimatedPrice: () => this._computeTotalEstimatedPrice(),
        });
    }

    /*
     * -------------------  Overrides ---------------------
     */

    /**
     * @override to add suggest context and filters if suggest is ON on first load.
     */
    async load(config) {
        Object.assign(this.suggest, {
            numberOfDays: config.context.vendor_suggest_days ?? this.suggest.numberOfDays,
            basedOn: config.context.vendor_suggest_based_on ?? this.suggest.basedOn,
            percentFactor: config.context.vendor_suggest_percent ?? this.suggest.percentFactor,
            suggestToggle: getSuggestToggleState(config.context.product_catalog_order_state),
        });
        if (this.suggest.suggestToggle.isOn) {
            // Add default filters for suggest before loading
            config.context["search_default_suggested"] = true;
            config.context["search_default_products_in_purchase_order"] = true;
        }
        await super.load(config);
        if (this.suggest.suggestToggle.isOn) {
            this._computeTotalEstimatedPrice();
        }
    }

    /**
     * @override inside of _notify (but only when searchpanel exists) to add ctx for
     * web_search_read but also to load correct categories, to compute correct total price ...
     */
    async _fetchSections() {
        this._editSuggestContext();
        super._fetchSections(...arguments);
    }

    /**
     * @override to recompute total price and add category_id to domain when selecting a category
     */
    toggleCategoryValue() {
        super.toggleCategoryValue(...arguments);
        if (this.suggest.suggestToggle.isOn) {
            this._computeTotalEstimatedPrice();
        }
    }

    /*
     * -------------------  Suggestion methods ---------------------
     */

    /** Calculate estimated price (might differ from actual PO price on purpose)
     *  if all suggestions where added to PO (ie. not only the ones displayed) */
    async _computeTotalEstimatedPrice() {
        this._editSuggestContext();
        const product_prices = await this.orm.searchRead(
            "product.product",
            this.domain,
            ["suggest_estimated_price"],
            { context: this.globalContext }
        );
        this.suggest.totalEstimatedPrice = product_prices.reduce(
            (sum, p) => sum + Number(p.suggest_estimated_price || 0),
            0
        );
    }

    /**
     * Toggles one or more filters based on filter name and desired states. Forces a refresh if no filter toggled
     * @param {Array[string]} filterNames eg. "suggested_or_ordered"
     * @param {boolean} turnOn eg. toggles filter "On" if turnOn = true and filter is currently "Off"
     */
    toggleFilters(filterNames, turnOn) {
        const searchFilters = new Map(Object.values(this.searchItems).map((i) => [i.name, i]));
        const activeFilters = new Set(this.query.map((q) => q.searchItemId));

        const toToggle = [];
        for (const name of filterNames) {
            const item = searchFilters.get(name);
            const isOn = activeFilters.has(item.id);
            if ((turnOn && !isOn) || (!turnOn && isOn)) {
                toToggle.push(item.id);
            }
        }

        // Prevent toggleSearchItem from trying to reload with partial domain
        for (let i = 0; i < toToggle.length; i++) {
            const isLast = i === toToggle.length - 1;
            this.blockNotification = !isLast;
            this.toggleSearchItem(toToggle[i]);
        }

        if (this.suggest.suggestToggle.isOn) {
            this._computeTotalEstimatedPrice();
        }
        if (toToggle.length == 0) {
            this._notify(); // Force reload, useful for eg. when toggling suggest off with filter already deactivated
        }
    }

    /**
     * Adds / Removes suggest parameters from globalContext depending if suggest feature is activated
     * @returns {Object} base context if suggest is OFF or base + suggest context
     */
    _editSuggestContext() {
        const suggestContext = {
            suggest_domain: this.domain,
            suggest_based_on: this.suggest.basedOn,
            suggest_days: this.suggest.numberOfDays,
            suggest_percent: this.suggest.percentFactor,
            sectionId: this.selectedSection.sectionId ?? false,
        };
        if (!this.suggest.suggestToggle.isOn) {
            for (const k of new Set([...Object.keys(suggestContext)])) {
                delete this.globalContext[k];
            }
        } else {
            this.globalContext = { ...this.globalContext, ...suggestContext };
        }
    }
}
