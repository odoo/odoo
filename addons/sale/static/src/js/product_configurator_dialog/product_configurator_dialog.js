import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { ProductList } from "../product_list/product_list";

export class ProductConfiguratorDialog extends Component {
    static components = { Dialog, ProductList};
    static template = 'sale.ProductConfiguratorDialog';
    static props = {
        productTemplateId: Number,
        ptavIds: { type: Array, element: Number },
        customPtavs: {
            type: Array,
            element: Object,
            shape: {
                id: Number,
                value: String,
            }
        },
        quantity: Number,
        productUOMId: { type: Number, optional: true },
        companyId: { type: Number, optional: true },
        pricelistId: { type: Number, optional: true },
        currencyId: { type: Number, optional: true },
        soDate: String,
        edit: { type: Boolean, optional: true },
        options: {
            type: Object,
            optional: true,
            shape: {
                canChangeVariant: { type: Boolean, optional: true },
                showQuantity : { type: Boolean, optional: true },
                showPrice : { type: Boolean, optional: true },
            },
        },
        save: Function,
        discard: Function,
        close: Function, // This is the close from the env of the Dialog Component
    };
    static defaultProps = {
        edit: false,
    }

    setup() {
        this.title = _t("Configure your product");
        this.env.dialogData.dismiss = !this.props.edit && this.props.discard.bind(this);
        this.state = useState({
            products: [],
            optionalProducts: [],
        });
        // Nest the currency id in an object so that it stays up to date in the `env`, even if we
        // modify it in `onWillStart` afterwards.
        this.currency = { id: this.props.currencyId };
        this.getValuesUrl = '/sale/product_configurator/get_values';
        this.createProductUrl = '/sale/product_configurator/create_product';
        this.updateCombinationUrl = '/sale/product_configurator/update_combination';
        this.getOptionalProductsUrl = '/sale/product_configurator/get_optional_products';

        useSubEnv({
            mainProductTmplId: this.props.productTemplateId,
            currency: this.currency,
            canChangeVariant: this.props.options?.canChangeVariant ?? true,
            showQuantity: this.props.options?.showQuantity ?? true,
            showPrice: this.props.options?.showPrice ?? true,
            addProduct: this._addProduct.bind(this),
            removeProduct: this._removeProduct.bind(this),
            setQuantity: this._setQuantity.bind(this),
            updateProductTemplateSelectedPTAV: this._updateProductTemplateSelectedPTAV.bind(this),
            updatePTAVCustomValue: this._updatePTAVCustomValue.bind(this),
            isPossibleCombination: this._isPossibleCombination,
        });

        onWillStart(async () => {
            const {
                products,
                optional_products,
                currency_id,
            } = await this._loadData(this.props.edit);
            this.state.products = products;
            this.state.optionalProducts = optional_products;
            for (const customPtav of this.props.customPtavs) {
                this._updatePTAVCustomValue(
                    this.env.mainProductTmplId,
                    customPtav.id,
                    customPtav.value
                );
            }
            this._checkExclusions(this.state.products[0]);
            // Use the currency id retrieved from the server if none was provided in the props.
            this.currency.id ??= currency_id;
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _loadData(onlyMainProduct) {
        return rpc(this.getValuesUrl, {
            product_template_id: this.props.productTemplateId,
            quantity: this.props.quantity,
            currency_id: this.currency.id,
            so_date: this.props.soDate,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
            ptav_ids: this.props.ptavIds,
            only_main_product: onlyMainProduct,
            ...this._getAdditionalRpcParams(),
        });
    }

    async _createProduct(product) {
        return rpc(this.createProductUrl, {
            product_template_id: product.product_tmpl_id,
            ptav_ids: this._getCombination(product),
        });
    }

    async _updateCombination(product, quantity) {
        return rpc(this.updateCombinationUrl, {
            product_template_id: product.product_tmpl_id,
            ptav_ids: this._getCombination(product),
            currency_id: this.currency.id,
            so_date: this.props.soDate,
            quantity: quantity,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
            ...this._getAdditionalRpcParams(),
        });
    }

    async _getOptionalProducts(product) {
        return rpc(this.getOptionalProductsUrl, {
            product_template_id: product.product_tmpl_id,
            ptav_ids: this._getCombination(product),
            parent_ptav_ids: this._getParentsCombination(product),
            currency_id: this.currency.id,
            so_date: this.props.soDate,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
            ...this._getAdditionalRpcParams(),
        });
    }

    /**
     * Hook to append additional RPC params in overriding modules.
     *
     * @return {Object} - The additional RPC params.
     */
    _getAdditionalRpcParams() {
        return {};
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
            // Filter out optional products that are already loaded in the configurator.
            const newOptionalProducts = (await this._getOptionalProducts(product)).filter(
                p => !this._findProduct(p.product_tmpl_id)
            );
            this.state.optionalProducts.push(...newOptionalProducts);
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
                this._removeProduct(childProduct.product_tmpl_id);
                this.state.optionalProducts.splice(
                    this.state.optionalProducts.findIndex(
                        p => p.product_tmpl_id === childProduct.product_tmpl_id
                    ), 1
                );
            }
        }
    }

    /**
     * Set the quantity of the product to a given value.
     *
     * If the value is less than or equal to zero, the product is removed from the product list
     * instead, unless it is the main product, in which case the quantity is set to 1.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} quantity - The new quantity of the product.
     * @return {Boolean} - Whether the quantity was updated.
     */
    async _setQuantity(productTmplId, quantity) {
        if (quantity <= 0) {
            if (productTmplId === this.env.mainProductTmplId) {
                quantity = 1;
            } else {
                this._removeProduct(productTmplId);
                return true;
            }
        }
        const product = this._findProduct(productTmplId);
        if (product.quantity === quantity) {
            return false;
        }
        const { price } = await this._updateCombination(product, quantity);
        product.quantity = quantity;
        product.price = parseFloat(price);
        return true;
    }

    /**
     * Change the value of `selected_attribute_value_ids` on the given PTAL in the product.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} ptalId - The PTAL id, as a `product.template.attribute.line` id.
     * @param {Number} ptavId - The PTAV id, as a `product.template.attribute.value` id.
     * @param {Boolean} isMulti - Whether multiple `product.template.attribute.value` can be selected.
     */
    async _updateProductTemplateSelectedPTAV(productTmplId, ptalId, ptavId, isMulti) {
        const product = this._findProduct(productTmplId);
        const ptal = product.attribute_lines.find(line => line.id === ptalId);
        ptavId = parseInt(ptavId);
        if (isMulti) {
            const selectedPtavIds = new Set(ptal.selected_attribute_value_ids);
            selectedPtavIds.has(ptavId)
                ? selectedPtavIds.delete(ptavId)
                : selectedPtavIds.add(ptavId);
            ptal.selected_attribute_value_ids = Array.from(selectedPtavIds);
        } else {
            ptal.selected_attribute_value_ids = [ptavId];
        }
        this._checkExclusions(product);
        if (this._isPossibleCombination(product)) {
            const updatedValues = await this._updateCombination(product, product.quantity);
            Object.assign(product, updatedValues);
            // When a combination should exist but was deleted from the database, it should not be
            // selectable and considered as an exclusion.
            if (!product.id && product.attribute_lines.every(ptal => ptal.create_variant === "always")) {
                const combination = this._getCombination(product);
                product.archived_combinations = product.archived_combinations.concat([combination]);
                this._checkExclusions(product);
            }
        }
    }

    /**
     * Set the custom value for a given custom PTAV.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} ptavId - The PTAV id, as a `product.template.attribute.value` id.
     * @param {String} customValue - The custom value.
     */
    _updatePTAVCustomValue(productTmplId, ptavId, customValue) {
        const product = this._findProduct(productTmplId);
        product.attribute_lines.find(
            ptal => ptal.selected_attribute_value_ids.includes(ptavId)
        ).customValue = customValue;
    }

    /**
     * Check the exclusions of a given product and his child.
     *
     * @param {Object} product - The product for which to check the exclusions.
     */
    _checkExclusions(product) {
        const combination = this._getCombination(product);
        const exclusions = product.exclusions;
        const parentExclusions = product.parent_exclusions;
        const archivedCombinations = product.archived_combinations;
        const parentCombination = this._getParentsCombination(product);
        const childProducts = this._getChildProducts(product.product_tmpl_id)
        const ptavList = product.attribute_lines.flat().flatMap(ptal => ptal.attribute_values)
        ptavList.map(ptav => ptav.excluded = false); // Reset all the values

        if (exclusions) {
            for(const ptavId of combination) {
                for(const excludedPtavId of exclusions[ptavId]) {
                    ptavList.find(ptav => ptav.id === excludedPtavId).excluded = true;
                }
            }
        }
        if (parentCombination) {
            for(const ptavId of parentCombination) {
                for(const excludedPtavId of (parentExclusions[ptavId]||[])) {
                    const ptav = ptavList.find(ptav => ptav.id === excludedPtavId);
                    if (ptav) {
                        ptav.excluded = true; // Assign only if the element exists
                    }
                }
            }
        }
        if (archivedCombinations) {
            for(const excludedCombination of archivedCombinations) {
                const ptavCommon = excludedCombination.filter((ptav) => combination.includes(ptav));
                if (ptavCommon.length === combination.length) {
                    for(const excludedPtavId of ptavCommon) {
                        ptavList.find(ptav => ptav.id === excludedPtavId).excluded = true;
                    }
                } else if (ptavCommon.length === (combination.length - 1)) {
                    // In this case we only need to disable the remaining ptav
                    const disabledPtavId = excludedCombination.find(
                        (ptav) => !combination.includes(ptav)
                    );
                    const excludedPtav = ptavList.find(ptav => ptav.id === disabledPtavId)
                    if (excludedPtav) {
                        excludedPtav.excluded = true;
                    }
                }
            }
        }
        for(const optionalProductTmpl of childProducts) {
            this._checkExclusions(optionalProductTmpl);
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Return the product given his template id.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @return {Object} - The product.
     */
    _findProduct(productTmplId) {
        // The product might be in either of the two lists `products` or `optional_products`.
        return  this.state.products.find(p => p.product_tmpl_id === productTmplId) ||
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
            ...this.state.products.filter(p => p.parent_product_tmpl_id === productTmplId),
            ...this.state.optionalProducts.filter(p => p.parent_product_tmpl_id === productTmplId)
        ]
    }

    /**
     * Return the selected PTAV of the product, as a list of `product.template.attribute.value` id.
     *
     * @param {Object} product - The product for which to find the combination.
     * @return {Array} - The combination of the product.
     */
    _getCombination(product) {
        return product.attribute_lines.flatMap(ptal => ptal.selected_attribute_value_ids);
    }

    /**
     * Return the selected PTAVs of the parent product, as a list of
     * `product.template.attribute.value` ids.
     *
     * @param {Object} product - The product for which to find the parent combination.
     * @return {Array} - The combination of the parent product.
     */
    _getParentsCombination(product) {
        return product.parent_product_tmpl_id
            ? this._getCombination(this._findProduct(product.parent_product_tmpl_id))
            : [];
    }

    /**
     * Check if a product has a valid combination.
     *
     * @param {Object} product - The product for which to check the combination.
     * @return {Boolean} - Whether the combination is valid or not.
     */
    _isPossibleCombination(product) {
        return product.attribute_lines.every(ptal => {
            const selectedPtavIds = new Set(ptal.selected_attribute_value_ids);
            return ptal.attribute_values
                .filter(ptav => selectedPtavIds.has(ptav.id))
                .every(ptav => !ptav.excluded);
        });
    }

    /**
     * Check if all the products selected have a valid combination.
     *
     * @return {Boolean} - Whether all the products selected have a valid combination or not.
     */
    isPossibleConfiguration() {
        return [...this.state.products].every(
            p => this._isPossibleCombination(p)
        );
    }

    /**
     * Confirm the current combination(s).
     *
     * @return {undefined}
     */
    async onConfirm(options) {
        if (!this.isPossibleConfiguration()) return;
        // Create the products with dynamic attributes
        for (const product of this.state.products) {
            if (
                !product.id &&
                product.attribute_lines.some(ptal => ptal.create_variant === "dynamic")
            ) {
                const productId = await this._createProduct(product);
                product.id = parseInt(productId);
            }
        }
        await this.props.save(
            this.state.products.find(
                p => p.product_tmpl_id === this.env.mainProductTmplId
            ),
            this.state.products.filter(
                p => p.product_tmpl_id !== this.env.mainProductTmplId
            ),
            options,
        );
        this.props.close();
    }

    /**
     * Discard the modal.
     */
    onDiscard() {
        if (!this.props.edit) {
            this.props.discard(); // clear the line
        }
        this.props.close();
    }
}
