/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Component, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from '@web/core/dialog/dialog';
import { Product } from "../product/product";
import { useService } from "@web/core/utils/hooks";

export class ProductConfiguratorDialog extends Component {
    static components = { Dialog, Product };
    static template = 'product.product_configurator.configuratorDialog';
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
        model: {type: String},
        quantity: { type: Number, optional: true },
        productUOMId: { type: Number, optional: true },
        companyId: { type: Number, optional: true },
        edit: { type: Boolean, optional: true },
        options: {
            type: Object,
            optional: true,
            shape: {
                showQty: { type: Boolean },
            }
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
        this.rpc = useService("rpc");
        this.state = useState({
            products: [],
        });

        useSubEnv({
            mainProductTmplId: this.props.productTemplateId,
            setQuantity: this._setQuantity.bind(this),
            updateProductTemplateSelectedPTAV: this._updateProductTemplateSelectedPTAV.bind(this),
            updatePTAVCustomValue: this._updatePTAVCustomValue.bind(this),
            isPossibleCombination: this._isPossibleCombination,
            options: {
                showQty: this.props.options?.showQty ?? true,
            }
        });

        onWillStart(async () => {
            await this.setState();
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

    async _loadData() {
        return this.rpc('/product_configurator/get_values', this._loadDataVals());
    }

    async _createProduct(product) {
        return this.rpc('/product_configurator/create_product', {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
        });
    }

    async _updateCombination(product, quantity) {
        return this.rpc('/product_configurator/update_combination', {
            ...this._updateCombinationVals(product, quantity)
        });
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Set the quantity of the product to a given value.
     *
     * The quantity must be strictly positive.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} quantity - The new quantity of the product.
     */
    async _setQuantity(productTmplId, quantity) {
        const product = this._findProduct(productTmplId);
        const updatedValues = await this._updateCombination(
            product,
            quantity > 0 && quantity || 1,
        );
        product.quantity = updatedValues.quantity;
        return updatedValues;
    }

    /**
     * Change the value of `selected_attribute_value_ids` on the given PTAL in the product.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @param {Number} ptalId - The PTAL id, as a `product.template.attribute.line` id.
     * @param {Number} ptavId - The PTAV id, as a `product.template.attribute.value` id.
     * @param {Boolean} multiIdsAllowed - Whether multiple `product.template.attribute.value` can be selected.
     */
    async _updateProductTemplateSelectedPTAV(productTmplId, ptalId, ptavId, multiIdsAllowed) {
        const product = this._findProduct(productTmplId);
        let selectedIds = product.attribute_lines.find(
            ptal => ptal.id === ptalId
        ).selected_attribute_value_ids;
        if (multiIdsAllowed) {
            const ptavID = parseInt(ptavId);
            if (!selectedIds.includes(ptavID)){
                selectedIds.push(ptavID);
            } else {
                selectedIds = selectedIds.filter(ptav => ptav !== ptavID);
            }

        } else {
            selectedIds = [parseInt(ptavId)];
        }
        product.attribute_lines.find(
            ptal => ptal.id === ptalId
        ).selected_attribute_value_ids = selectedIds;
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
            ptal => ptal.selected_attribute_value_ids.includes(ptavId)
        ).customValue = customValue;
    }

    /**
     * Check the exclusions of a given product.
     *
     * @param {Object} product - The product for which to check the exclusions.
     */
    _checkExclusions(product) {
        const combination = this._getCombination(product);
        const exclusions = product.exclusions;
        const archivedCombinations = product.archived_combinations;
        const ptavList = product.attribute_lines.flat().flatMap(ptal => ptal.attribute_values)
        ptavList.map(ptav => ptav.excluded = false); // Reset all the values

        if (exclusions) {
            for(const ptavId of combination) {
                for(const excludedPtavId of exclusions[ptavId]) {
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
                    const excludedPtav = ptavList.find(ptav => ptav.id === disabledPtavId)
                    if (excludedPtav) {
                        excludedPtav.excluded = true;
                    }
                }
            }
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Load the products from the controller to the state.
     *
     * For a module to customize the state, it needs to override this method and call `super` to get
     * the values.
     *
     * @returns {Object} - The values returned by the server.
     */
    async setState() {
        const productConfiguratorValues = await this._loadData();
        this.state.products = productConfiguratorValues.products;
        return productConfiguratorValues;
    }

    /** @returns {Object} - The values to send to the serveur when loading the data */
    _loadDataVals() {
        let vals = {
            product_template_id: this.props.productTemplateId,
            company_id: this.props.companyId,
            ptav_ids: this.props.ptavIds,
            model: this.props.model
        };
        if (this.env.options.showQty) {
            vals['quantity'] = this.props.quantity;
            vals['product_uom_id'] = this.props.productUOMId;
        }
        return vals;
    }

    /**
     *
     * @param {Object} product - The product to update
     * @param {Number} quantity - The quantity of the product
     * @returns {Object} - The values to send to the serveur when updatating the combination
     */
    _updateCombinationVals(product, quantity) {
        let vals = {
            product_template_id: product.product_tmpl_id,
            combination: this._getCombination(product),
            company_id: this.props.companyId,
            model: this.props.model
        };
        if (this.env.options.showQty) {
            vals['quantity'] = quantity;
            vals['product_uom_id'] = this.props.productUOMId;
        }
        return vals;
    }

    /**
     * Return the product given his template id.
     *
     * @param {Number} productTmplId - The product template id, as a `product.template` id.
     * @return {Object} - The product.
     */
    _findProduct(productTmplId) {
        // The product might be in the lists`products``.
        return  this.state.products.find(p => p.product_tmpl_id === productTmplId);
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
     * Check if a product has a valid combination.
     *
     * @param {Object} product - The product for which to check the combination.
     * @return {Boolean} - Whether the combination is valid or not.
     */
    _isPossibleCombination(product) {
        return product.attribute_lines.every(ptal => !ptal.attribute_values.find(
            ptav => ptal.selected_attribute_value_ids.includes(ptav.id)
        )?.excluded);
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
            this.state.products.find(
                p => p.product_tmpl_id === this.env.mainProductTmplId
            ),
            this.state.products.filter(
                p => p.product_tmpl_id !== this.env.mainProductTmplId
            ),
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
