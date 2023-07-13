/** @odoo-module */

import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { ProductList } from "../product_list/product_list";
import { useService } from "@web/core/utils/hooks";

export class ProductConfiguratorDialog extends Component {
    static components = { Dialog, ProductList};
    static template = 'sale_product_configurator.dialog';
    static props = {
        productTemplateId: Number,
        ptavIds: { type: Array, element: Number },
        customAttributeValues: {
            type: Array,
            element: Object,
            shape: {
                ptavId: Number,
                value: String,
            }
        },
        quantity: Number,
        productUOMId: { type: Number, optional: true },
        companyId: { type: Number, optional: true },
        pricelistId: { type: Number, optional: true },
        currencyId: Number,
        soDate: String,
        edit: { type: Boolean, optional: true },
        save: Function,
        discard: Function,
        close: Function, // This is the close from the env of the Dialog Component
    };
    static defaultProps = {
        edit: false,
    }

    setup() {
        this.title = this.env._t("Configure");
        this.rpc = useService("rpc");
        this.state = useState({
            products: [],
            optionalProducts: [],
        });

        useSubEnv({
            mainProductTmplId: this.props.productTemplateId,
            currencyId: this.props.currencyId,
            addProduct: this._addProduct.bind(this),
            removeProduct: this._removeProduct.bind(this),
            setQuantity: this._setQuantity.bind(this),
            updateProductTemplateSelectedPTAV: this._updateProductTemplateSelectedPTAV.bind(this),
            updatePTAVCustomValue: this._updatePTAVCustomValue.bind(this),
            isPossibleCombination: this._isPossibleCombination,
        });

        onWillStart(async () => {
            const { products, optional_products } = await this._loadData(this.props.edit);
            this.state.products = products;
            this.state.optionalProducts = optional_products;
            for (const customValue of this.props.customAttributeValues) {
                this._updatePTAVCustomValue(
                    this.env.mainProductTmplId,
                    customValue.ptavId,
                    customValue.value
                );
            }
            this._checkExclusions(this.state.products[0]);
        });
    }

    //--------------------------------------------------------------------------
    // Data Exchanges
    //--------------------------------------------------------------------------

    async _loadData(onlyMainProduct) {
        return this.rpc('/sale_product_configurator/get_values', {
            product_template_id: this.props.productTemplateId,
            quantity: this.props.quantity,
            currency_id: this.props.currencyId,
            so_date: this.props.soDate,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
            ptav_ids: this.props.ptavIds,
            only_main_product: onlyMainProduct,
        });
    }

    async _createProduct(product) {
        return this.rpc('/sale_product_configurator/create_product', {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
        });
    }

    async _updateCombination(product, quantity) {
        return this.rpc('/sale_product_configurator/update_combination', {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
            currency_id: this.props.currencyId,
            so_date: this.props.soDate,
            quantity: quantity,
            product_uom_id: this.props.productUOMId,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
        });
    }

    async _getOptionalProducts(product) {
        return this.rpc('/sale_product_configurator/get_optional_products', {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
            parent_combination: this._getParentsCombination(product),
            currency_id: this.props.currencyId,
            so_date: this.props.soDate,
            company_id: this.props.companyId,
            pricelist_id: this.props.pricelistId,
        });
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
            const newOptionalProducts = await this._getOptionalProducts(product);
            for(const newOptionalProductDict of newOptionalProducts) {
                // If the optional product is already in the list, add the id of the parent product
                // template in his list of `parent_product_tmpl_ids` instead of adding a second time
                // the product.
                const newProduct = this._findProduct(newOptionalProductDict.product_tmpl_id);
                if (newProduct) {
                    newOptionalProducts.pop(newOptionalProductDict);
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
        if (quantity <= 0) {
            if (productTmplId === this.env.mainProductTmplId) {
                const product = this._findProduct(productTmplId);
                const { price } = await this._updateCombination(product, 1);
                product.quantity = 1;
                product.price = parseFloat(price);
                return;
            };
            this._removeProduct(productTmplId);
        } else {
            const product = this._findProduct(productTmplId);
            const { price } = await this._updateCombination(product, quantity);
            product.quantity = quantity;
            product.price = parseFloat(price);
        }
    }

    /**
     * Change the value of `selected_attribute_value_id` on the given PTAL in the product.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} ptalId - The PTAL id, as a `product.template.attribute.line` id.
     * @param {Number} ptavId - The PTAV id, as a `product.template.attribute.value` id.
     */
    async _updateProductTemplateSelectedPTAV(productTmplId, ptalId, ptavId) {
        const product = this._findProduct(productTmplId);
        product.attribute_lines.find(
            ptal => ptal.id === ptalId
        ).selected_attribute_value_id = parseInt(ptavId);
        this._checkExclusions(product);
        if (this._isPossibleCombination(product)) {
            const updatedValues = await this._updateCombination(product, product.quantity);
            Object.assign(product, updatedValues);
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
            ptal => ptal.selected_attribute_value_id === ptavId
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
                    ptavList.find(ptav => ptav.id === excludedPtavId).excluded = true;
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
                    if (disabledPtavId) {
                        ptavList.find(ptav => ptav.id === disabledPtavId).excluded = true;
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
            ...this.state.products.filter(p => p.parent_product_tmpl_ids?.includes(productTmplId)),
            ...this.state.optionalProducts.filter(p => p.parent_product_tmpl_ids?.includes(productTmplId))
        ]
    }

    /**
     * Return the selected PTAV of the product, as a list of `product.template.attribute.value` id.
     *
     * @param {Object} product - The product for which to find the combination.
     * @return {Array} - The combination of the product.
     */
    _getCombination(product) {
        return product.attribute_lines.map(ptal => ptal.selected_attribute_value_id);
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

    /**
     * Check if a product has a valid combination.
     *
     * @param {Object} product - The product for which to check the combination.
     * @return {Boolean} - Whether the combination is valid or not.
     */
    _isPossibleCombination(product) {
        return product.attribute_lines.every(ptal => !ptal.attribute_values.find(
            ptav => ptav.id === ptal.selected_attribute_value_id
        ).excluded);
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
     * Serialize the product into a format understandable by `sale.order.line`.
     *
     * @param {Object} product - The product to serialize.
     * @return {Object} - The serialized product.
     */
    _serializeProduct(product) {
        let serializedProduct = {
            product_id: [product.id, product.display_name],
            product_uom_qty: product.quantity,
        }

        // handle custom values & no variants
        let customValuesCommands = [{ operation: "DELETE_ALL" }];
        for (const ptal of product.attribute_lines) {
            const selectedCustomPTAV = ptal.attribute_values.find(
                ptav => ptav.is_custom && ptav.id === ptal.selected_attribute_value_id
            );
            if (selectedCustomPTAV) customValuesCommands.push({
                operation: "CREATE",
                context: [
                    {
                        default_custom_product_template_attribute_value_id: selectedCustomPTAV.id,
                        default_custom_value: ptal.customValue,
                    },
                ],
            });
        }
        serializedProduct.product_custom_attribute_value_ids = {
            operation: "MULTI",
            commands: customValuesCommands,
        };

        let noVariantCommands = [{ operation: "DELETE_ALL" }];
        const noVariantPTAVIds = product.attribute_lines.filter(
            ptal => ptal.create_variant === "no_variant" && ptal.attribute_values.length > 1
        ).map(ptal => { return {id: ptal.selected_attribute_value_id}});
        if (noVariantPTAVIds.length) noVariantCommands.push({
            operation: "ADD_M2M",
            ids: noVariantPTAVIds,
        });
        serializedProduct.product_no_variant_attribute_value_ids = {
            operation: "MULTI",
            commands: noVariantCommands,
        };

        return serializedProduct;
    }

    /**
     * Confirm the current combination(s).
     *
     * @return {undefined}
     */
    async onConfirm() {
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
            this._serializeProduct(this.state.products.find(
                p => p.product_tmpl_id === this.env.mainProductTmplId
            )),
            this.state.products.filter(
                p => p.product_tmpl_id !== this.env.mainProductTmplId
            ).map(p => this._serializeProduct(p)),
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
