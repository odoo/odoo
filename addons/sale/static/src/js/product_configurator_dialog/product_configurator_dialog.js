/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useState, useSubEnv } from "@odoo/owl";
import { ProductConfiguratorDialog } from "@product/js/product_configurator/product_configurator_dialog/product_configurator_dialog";
import { ProductList } from "../product_list/product_list";

export class SaleProductConfiguratorDialog extends ProductConfiguratorDialog {
    static components = { ...ProductConfiguratorDialog.components, ProductList };
    static template = 'sale_product_configurator.configuratorDialog';
    static props = {
        ...ProductConfiguratorDialog.props,
        pricelistId: { type: Number, optional: true },
        currencyId: Number,
        soDate: String,
    };
    setup() {
        this.title = _t("Configure your product");

        super.setup();
        this.state = useState({
            products: [],
            optionalProducts: [],
        });
        useSubEnv({
            ...this.env,
            currencyId: this.props.currencyId,
            addProduct: this._addProduct.bind(this),
            removeProduct: this._removeProduct.bind(this),
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _getOptionalProducts(product) {
        let params = {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
            parent_combination: this._getParentsCombination(product),
            currency_id: this.props.currencyId,
            so_date: this.props.soDate,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
            model: this.props.model,
        };
        if (this.env.options.showQty) {
            params['quantity'] = 1;
        }
        return this.rpc('/product_configurator/get_optional_products', params);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Add the product to the list of products and fetch his optional products.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     */
    async _addProduct(productTmplId) {
        const index = this.state.optionalProducts.findIndex(
            p => p.product_tmpl_id === productTmplId
        );
        if (index >= 0) {
            this.state.products.push(...this.state.optionalProducts.splice(index, 1));
            // Fetch optional product from the server with the parent combination.
            const product = this._findProduct(productTmplId);
            let newOptionalProducts = await this._getOptionalProducts(product);
            for (const newOptionalProductDict of newOptionalProducts) {
                // If the optional product is already in the list, add the id of the parent product
                // template in his list of `parent_product_tmpl_ids` instead of adding a second time
                // the product.
                const newProduct = this._findProduct(newOptionalProductDict.product_tmpl_id);
                if (newProduct) {
                    newOptionalProducts = newOptionalProducts.filter(
                        (p) => p.product_tmpl_id != newOptionalProductDict.product_tmpl_id
                    );
                    newProduct.parent_product_tmpl_ids.push(productTmplId);
                }
            }
            if (newOptionalProducts) this.state.optionalProducts.push(...newOptionalProducts);
        }
    }

    /**
     * Remove the product and his optional products from the list of products.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     */
    _removeProduct(productTmplId) {
        const index = this.state.products.findIndex(p => p.product_tmpl_id === productTmplId);
        if (index >= 0) {
            this.state.optionalProducts.push(...this.state.products.splice(index, 1));
            for (const childProduct of this._getChildProducts(productTmplId)) {
                // Optional products might have multiple parents so we don't want to remove them if
                // any of their parents are still on the list of products.
                childProduct.parent_product_tmpl_ids = childProduct.parent_product_tmpl_ids.filter(
                    id => id !== productTmplId
                );
                if (!childProduct.parent_product_tmpl_ids.length) {
                    this._removeProduct(childProduct.product_tmpl_id);
                    this.state.optionalProducts.splice(
                        this.state.optionalProducts.findIndex(
                            p => p.product_tmpl_id === childProduct.product_tmpl_id
                        ), 1
                    );
                }
            }
        }
    }

    /**
     * Set the quantity of the product to a given value.
     *
     * If the value is less than or equal to zero, the product is removed from the product list
     * instead, unless it is the main product, in which case the changes are ignored.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} quantity - The new quantity of the product.
     */
    async _setQuantity(productTmplId, quantity) {
        const updatedValues = await super._setQuantity(productTmplId, quantity);
        const product = this._findProduct(productTmplId);
        product.price = parseFloat(updatedValues.price);
        if (productTmplId !== this.env.mainProductTmplId && quantity <= 0) {
            this._removeProduct(productTmplId);
        };
    }

    /**
     * Override of `product` to also check the exclusions its child.
     *
     * @param {Object} product - The product for which to check the exclusions.
     * @param {undefined|Array} checked - The array of products checked for exclusions, used to
     * avoid infinite check exclusions for recursive optional products.
     */
    _checkExclusions(product, checked=undefined) {
        super._checkExclusions(product);
        const parentExclusions = product.parent_exclusions;
        const parentCombination = this._getParentsCombination(product);
        const childProducts = this._getChildProducts(product.product_tmpl_id);
        const ptavList = product.attribute_lines.flat().flatMap(ptal => ptal.attribute_values);

        if (parentCombination) {
            for (const ptavId of parentCombination) {
                for (const excludedPtavId of parentExclusions[ptavId] || []) {
                    ptavList.find(ptav => ptav.id === excludedPtavId).excluded = true;
                }
            }
        }
        const checkedProducts = checked || [];
        for (const optionalProductTmpl of childProducts) {
             // if the product is not checked for exclusions
            if (!checkedProducts.includes(optionalProductTmpl)) {
                checkedProducts.push(optionalProductTmpl); // remember that this product is checked
                this._checkExclusions(optionalProductTmpl, checkedProducts);
            }
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Override of `product` to add an optional products in the state.
     *
     * @returns {Object} - The values returned by the server.
     */
    async setState() {
        const productConfiguratorValues = await super.setState();
        this.state.optionalProducts = productConfiguratorValues.optional_products ?? [];
        return productConfiguratorValues;
    }

    /**
     * Override of `product` to add the data needed for `sale`.
     *
     * @returns {Object} - The values to send to the serveur when loading the data
     */
    _loadDataVals() {
        return {
            ...super._loadDataVals(),
            currency_id: this.props.currencyId,
            so_date: this.props.soDate,
            pricelist_id: this.props.pricelistId,
            only_main_product: this.props.edit,
        };
    }

    /**
     * Override of `product` to add the data needed for `sale`.
     *
     * @param {Object} product - The product to update
     * @param {Number} quantity - The quantity of the product
     * @returns {Object} - The values to send to the serveur when updatating the combination
     */
    _updateCombinationVals(product, quantity) {
        return {
            ...super._updateCombinationVals(product, quantity),
            currency_id: this.props.currencyId,
            so_date: this.props.soDate,
            pricelist_id: this.props.pricelistId,
        };
    }

    /**
     * Override of `product` to also look for the product in `optionalProducts` list.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @return {Object} - The product.
     */
    _findProduct(productTmplId) {
        // The product might be in either of the two lists `products` or `optionalProducts`.
        return super._findProduct(productTmplId) ||
               this.state.optionalProducts.find(p => p.product_tmpl_id === productTmplId);
    }

    /**
     * Return the list of dependents products for a given product.
     *
     * @param {Number} productTmplId - The product template id for which to find his children, as a
     *                                 `product.template` id.
     * @return {Array} - The list of dependents products.
     */
    _getChildProducts(productTmplId) {
        return [
            ...this.state.products.filter(p => p.parent_product_tmpl_ids?.includes(productTmplId)),
            ...this.state.optionalProducts?.filter(p => p.parent_product_tmpl_ids?.includes(productTmplId))
        ]
    }

    /**
     * Return the selected PTAV of all the product parents, as a list of
     * `product.template.attribute.value` id.
     *
     * @param {Object} product - The product for which to find the combination.
     * @return {Array} - The combination of the product.
     */
    _getParentsCombination(product) {
        let parentsCombination = [];
        for(const parentProductTmplId of product.parent_product_tmpl_ids || []) {
            parentsCombination.push(this._getCombination(this._findProduct(parentProductTmplId)));
        }
        return parentsCombination.flat();
    }
}
