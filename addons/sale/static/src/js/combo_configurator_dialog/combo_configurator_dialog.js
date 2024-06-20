import { Dialog } from '@web/core/dialog/dialog';
import { useService } from '@web/core/utils/hooks';
import { Component, useState, useSubEnv } from '@odoo/owl';
import { ProductCard } from '../product_card/product_card';
import {
    ProductConfiguratorDialog
} from '../product_configurator_dialog/product_configurator_dialog';

/**
 * @typedef {{
 *     id: number,
 *     name: string,
 *     comboItems: ComboItem[],
 * }} Combo
 * @typedef {{
 *     id: number,
 *     product: Product,
 *     extraPrice?: number,
 * }} ComboItem
 * @typedef {{
 *     id: number,
 *     name: string,
 *     ptavIds: number[],
 *     customPtavs: CustomPtav[]
 * }} Product
 * @typedef {{
 *     ptavId: number,
 *     value: string,
 * }} CustomPtav
 */

export class ComboConfiguratorDialog extends Component {
    static template = 'sale.ComboConfiguratorDialog';
    static components = { ProductCard, Dialog };
    static props = {
        // TODO(loti): only provide product template id, selected product ids, and ptav ids?
        // (and get the necessary fields via RPCs?)
        name: String,
        combos: {
            type: Array,
            element: Object,
            shape: {
                id: Number,
                name: String,
                comboItems: {
                    type: Array,
                    element: Object,
                    shape: {
                        id: Number,
                        isSelected: Boolean,
                        extraPrice: { type: Number, optional: true },
                        product: {
                            type: Object,
                            shape: {
                                id: Number,
                                productTemplateId: Number,
                                name: String,
                                // TODO(loti): only provide ptav ids or also all necessary fields?
                                ptavIds: { type: Array, element: Number },
                                customPtavs: {
                                    type: Array,
                                    element: Object,
                                    shape: {
                                        ptavId: Number,
                                        value: String,
                                    },
                                },
                            },
                        },
                    },
                },
            },
        },
        companyId: { type: Number, optional: true },
        pricelistId: { type: Number, optional: true },
        currencyId: { type: Number, optional: true },
        date: String,
        edit: { type: Boolean, optional: true },
        save: Function,
        discard: Function,
        close: Function, // This is the close from the env of the Dialog Component.
    };

    setup() {
        this.dialog = useService("dialog");
        this.state = useState({
            // Maps combo ids to selected combo items.
            // Shape: Map<Number, {id: Number, ptavIds: Number[], customPtavs: CustomPtav[]}>
            selectedComboItems: new Map(this.props.combos.map(c => [
                c.id,
                c.comboItems.find(cl => cl.isSelected).map(cl => ({
                    id: cl.id,
                    ptavIds: cl.product.ptavIds,
                    customPtavs: cl.product.customPtavs
                }))
            ])),
        });
        this.currency = { id: this.props.currencyId };
        useSubEnv({
            currency: this.currency,
        });
    }

    /**
     * Check whether a combo item has been selected for each combo.
     *
     * @return {Boolean} Whether a combo item has been selected for each combo.
     */
    areAllCombosSelected() {
        return this.state.selectedComboItems.size === this.props.combos.length;
    }

    async onClickProduct(product) {
        if (product.isConfigurable()) {
            // TODO(loti): display product configurator dialog. Switch content via animation?
            this.dialog.add(ProductConfiguratorDialog, {
                productTemplateId: product.productTemplateId,
                ptavIds: product.ptavIds,
                customAttributeValues: product.customPtavs,
                quantity: 1,
                companyId: this.props.companyId,
                pricelistId: this.props.pricelistId,
                currencyId: this.props.currencyId,
                soDate: this.props.date,
                edit: true, // TODO(loti)
                save: async (configuredProduct) => {
                    product.ptavIds = configuredProduct.attribute_lines
                        .flatMap(ptal => ptal.selected_attribute_value_ids);
                    const customPtavs = [];
                    // TODO(loti): we use the same logic in web configurator => use shared method.
                    for (const ptal of configuredProduct.attribute_lines) {
                        const selectedPtavIds = new Set(ptal.selected_attribute_value_ids);
                        const selectedCustomPtav = ptal.attribute_values.find(
                            ptav => ptav.is_custom && selectedPtavIds.has(ptav.id)
                        );
                        if (selectedCustomPtav) {
                            customPtavs.push({
                                ptavId: selectedCustomPtav.id,
                                value: ptal.customValue,
                            });
                        }
                    }
                    product.customPtavs = customPtavs;
                },
                discard: () => {
                    this.state.selectedComboItems.delete(combo.id);
                },
            });
        }
    }

    async confirm() {
        await this.props.save(this.state.selectedComboItems.values());
        this.props.close();
    }

    cancel() {
        if (!this.props.edit) {
            this.props.discard();
        }
        this.props.close();
    }
}
