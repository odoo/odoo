/** @odoo-module **/

import { registry, Widget } from "web.public.widget";
import { WebsiteSaleCartButtonParent } from "./website_sale_cart_button";

/**
 * This widget is responsible for any logic necessary on the /shop page.
 *
 * NOTE: extending twice as extending once with multiple arguments does not yield the correct result.
 */
export const WebsiteSaleShop = Widget.extend(WebsiteSaleCartButtonParent).extend({
    selector: "#wrap.o_wsale_products_page",
    // We do this to avoid registering a widget per button.
    addToCartButtonSelector: ".o_wsale_products_grid_table_wrapper",
    cartButtonAdditionalSelector: ".o_wsale_product_btn .btn",
    events: {
        // Offcanvas
        "show.bs.offcanvas #o_wsale_offcanvas": "toggleFilters",
        "hidden.bs.offcanvas #o_wsale_offcanvas": "toggleFilters",
        // Filters, search and options
        "submit .o_wsale_products_searchbar_form": "onSubmitSearch",
        'newRangeValue #o_wsale_price_range_option input[type="range"]': "onPriceRangeSelected",
        "change form.js_attributes input, form.js_attributes select": "onChangeAttribute",
        "click [data-link-href]": "onClickLink",
    },

    start() {
        const result = this._super(...arguments);
        this.productGridEl = this.el.querySelector(".o_wsale_products_grid_table_wrapper");
        return result;
    },

    // Offcanvas

    /**
     * Unfold active filters, fold inactive ones.
     */
    toggleFilters(ev) {
        for (const btn of this.el.querySelectorAll("button[data-status]")) {
            if (
                (btn.classList.contains("collapsed") && btn.dataset.status == "active") ||
                (!btn.classList.contains("collapsed") && btn.dataset.status == "inactive")
            ) {
                btn.click();
            }
        }
    },

    // Filters and options

    /**
     * Increase the product grid's opacity.
     * Used when applying new filters for visual feedback.
     */
    _obscureProductGrid() {
        if (!this.productGridEl) {
            return;
        }
        this.productGridEl.classList.add("opacity-50");
    },

    /**
     * Redirects to the same page, using the query keys and values as arguments.
     * If a pending query is still loading, that query is used as base instead of the url.
     *
     * @param {Object} query new key/values to use, undefined value means removing the key.
     * @param {Boolean} keepQuery whether or not to reset the query completely and just use the given query
     */
    _redirectNewQuery(query, keepQuery = true) {
        const newQuery = (keepQuery && this.pendingQuery || new URLSearchParams(window.location.search)) || new URLSearchParams();
        for (const [key, value] of Object.entries(query)) {
            if (value === undefined) {
                newQuery.delete(key);
            } else {
                newQuery.set(key, value);
            }
        }
        this._redirectQuery(newQuery);
    },

    /**
     * Properly redirects to the current page given the new params.
     * If no params are to be set, no url arguments are set.
     * Also removes empty values.
     *
     * @param {URLSearchParams} query
     */
    _redirectQuery(query) {
        const keysToRemove = [];
        for (const [k, v] of query.entries()) {
            if (!encodeURIComponent(v).length) {
                keysToRemove.push(k);
            }
        }
        keysToRemove.forEach((k) => query.delete(k));
        let searchString = encodeURI(query);
        if (searchString) {
            searchString = "?" + searchString;
        }
        this._obscureProductGrid();
        this.pendingQuery = query;
        window.location.href = window.location.pathname + searchString;
    },

    /**
     * Handle new search, when querying a new string,
     * make sure we keep all current filters.
     *
     * @param {SubmitEvent} ev event
     */
    onSubmitSearch(ev) {
        if (ev.isDefaultPrevented() || ev.currentTarget.classList.contains("disabled")) {
            return;
        }
        ev.preventDefault();
        const searchInput = ev.currentTarget.querySelector("input.search-query");
        this._redirectNewQuery({ [searchInput.name]: encodeURIComponent(searchInput.value) });
    },

    /**
     * Handle change of price filter.
     */
    onPriceRangeSelected(ev) {
        const range = ev.currentTarget;
        this._redirectNewQuery({
            min_price: parseFloat(range) !== range.valueLow ? range.valueLow : undefined,
            max_price: parseFloat(range) !== range.valueHigh ? range.valueHigh : undefined,
        });
    },

    /**
     * Handle change of attribute filter
     */
    onChangeAttribute(ev) {
        if (ev.isDefaultPrevented()) {
            return;
        }
        ev.preventDefault();
        const target = ev.currentTarget;
        // We have 2 cases, a checkbox or a select
        const valuesToRemove = [];
        let valueToAdd = undefined;
        switch (target.tagName) {
            case "INPUT":
                if (target.checked) {
                    valueToAdd = target.value;
                } else {
                    valuesToRemove.push(target.value);
                }
                break;
            case "SELECT":
                const optionValues = [...target.options].map((opt) => opt.value);
                if (target.value.length) {
                    // Value Selected
                    valuesToRemove.push(...optionValues.filter((opt) => opt !== target.value));
                    valueToAdd = target.value;
                } else {
                    // Value removed
                    valuesToRemove.push(...optionValues);
                }
                break;
        }
        // Initial value
        const searchParams = this.pendingQuery || new URLSearchParams(window.location.search);
        let attribQueryOpt = searchParams.getAll("attrib") || [];
        // Remove invalid values
        attribQueryOpt = attribQueryOpt.filter((opt) => !valuesToRemove.includes(opt));
        // Add new value
        if (valueToAdd) {
            attribQueryOpt.push(valueToAdd);
        }
        searchParams.delete("attrib");
        if (attribQueryOpt) {
            for (const attrib of attribQueryOpt) {
                searchParams.append("attrib", attrib);
            }
        }
        this._redirectQuery(searchParams);
    },

    /**
     * Visual feedback when clicking on a link.
     */
    onClickLink(ev) {
        this._obscureProductGrid();
        window.location.href = ev.currentTarget.dataset.linkHref;
    },

    // Add to cart

    /**
     * The button element actually contains the information we need
     *
     * @override
     */
    getProductInfo(ev) {
        const target = ev.data.currentTarget;
        Object.assign(ev.data.productInfo, {
            product_id: target.dataset.productId,
            product_template_id: target.dataset.productTemplateId,
        });
    },
});

registry.WebsiteSaleShop = WebsiteSaleShop;
