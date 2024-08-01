import { Dialog } from '@web/core/dialog/dialog';
import { formatCurrency } from '@web/core/currency';
import { rpc } from '@web/core/network/rpc';
import { useService } from '@web/core/utils/hooks';
import { Component, useState, useSubEnv } from '@odoo/owl';
import { ProductCard } from '../product_card/product_card';
import { ProductCombo } from '../models/product_combo';
import { ProductTemplateAttributeLine } from '../models/product_template_attribute_line';
import {
    ProductConfiguratorDialog
} from '../product_configurator_dialog/product_configurator_dialog';
import { QuantityButtons } from '../quantity_buttons/quantity_buttons';

export class ComboConfiguratorDialog extends Component {
    static template = 'sale.ComboConfiguratorDialog';
    static components = { Dialog, ProductCard, QuantityButtons };
    static props = {
        product_tmpl_id: Number,
        display_name: String,
        quantity: Number,
        price: Number,
        combos: { type: Array, element: ProductCombo },
        currency_id: { type: Number, optional: true },
        company_id: { type: Number, optional: true },
        pricelist_id: { type: Number, optional: true },
        date: String,
        edit: { type: Boolean, optional: true },
        save: Function,
        discard: Function,
        close: Function,
    };

    setup() {
        this.dialog = useService('dialog');
        this.env.dialogData.dismiss = !this.props.edit && this.props.discard.bind(this);
        this.state = useState({
            // Maps combo ids to selected combo items.
            // Note that selected combo items can be modified (i.e. their `no_variant` PTAVs can be
            // updated), so this map stores deep copies to avoid modifying the props.
            selectedComboItems: new Map(),
            quantity: this.props.quantity,
            basePrice: this.props.price,
        });
        if (this.props.edit) this._initSelectedComboItems();
        this._selectSingleComboItems();
        this.getPriceUrl = '/sale/combo_configurator/get_price';
        useSubEnv({ currency: { id: this.props.currency_id } });
    }

    /**
     * Select the provided combo item, and open the product configurator iff the combo item's
     * product is configurable.
     *
     * @param {Number} comboId The id of the combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item to select.
     */
    async selectComboItem(comboId, comboItem) {
        // Use up-to-date selected PTAVs and custom values to populate the product configurator.
        comboItem = this.getSelectedOrProvidedComboItem(comboId, comboItem);
        let product = comboItem.product;
        if (product.hasNoVariantPtals) {
            // TODO(loti): replace content instead of stacking dialogs?
            this.dialog.add(ProductConfiguratorDialog, {
                productTemplateId: product.product_tmpl_id,
                ptavIds: product.selectedPtavIds,
                customPtavs: product.selectedCustomPtavs,
                quantity: 1,
                companyId: this.props.company_id,
                pricelistId: this.props.pricelist_id,
                currencyId: this.props.currency_id,
                soDate: this.props.date,
                edit: true, // TODO(loti): this "disables" optional products. Rename variable for clarity?
                options: { canChangeVariant: false, showQuantityAndPrice: false },
                save: async configuredProduct => {
                    const selectedComboItem = comboItem.deepCopy();
                    selectedComboItem.product.ptals = configuredProduct.attribute_lines.map(
                        ProductTemplateAttributeLine.fromProductConfiguratorPtal
                    );
                    this.state.selectedComboItems.set(comboId, selectedComboItem);
                },
                discard: () => {},
            });
        } else {
            this.state.selectedComboItems.set(comboId, comboItem.deepCopy());
        }
    }

    /**
     * Sets the quantity of this combo product.
     *
     * @param {Number} quantity The new quantity of this combo product.
     */
    async setQuantity(quantity) {
        this.state.quantity = quantity;
        this.state.basePrice = await rpc(this.getPriceUrl, {
            product_tmpl_id: this.props.product_tmpl_id,
            currency_id: this.props.currency_id,
            quantity: quantity,
            date: this.props.date,
            company_id: this.props.company_id,
            pricelist_id: this.props.pricelist_id,
        });
    }

    /**
     * Return the selected or provided combo item.
     *
     * If the provided combo item was already selected, then it may contain stale data (i.e.
     * selected PTAVs, custom values), and we should rely on the data in `state.selectedComboItems`
     * instead. Otherwise, the data in the provided combo item is up-to-date and can be used.
     *
     * @param {Number} comboId The id of the combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The provided combo item.
     * @return {ProductComboItem} The selected or provided combo item.
     */
    getSelectedOrProvidedComboItem(comboId, comboItem) {
        const selectedComboItem = this.state.selectedComboItems.get(comboId);
        const isComboItemAlreadySelected = selectedComboItem?.id === comboItem.id;
        return isComboItemAlreadySelected ? selectedComboItem : comboItem;
    }

    /**
     * Return the total price, formatted using the provided currency.
     *
     * The total price is the sum of:
     * - The combo product's price,
     * - The selected combo items' extra price,
     * - The selected `no_variant` attributes' extra price.
     *
     * @return {String} The formatted total price.
     */
    get formattedTotalPrice() {
        return formatCurrency(this._totalPrice, this.props.currency_id);
    }

    /**
     * Check whether a combo item has been selected for each combo.
     *
     * @return {Boolean} Whether a combo item has been selected for each combo.
     */
    get areAllCombosSelected() {
        return this.state.selectedComboItems.size === this.props.combos.length;
    }

    async confirm(options) {
        await this.props.save(this._comboProductData, this._selectedComboItems, options);
        this.props.close();
    }

    cancel() {
        if (!this.props.edit) {
            this.props.discard();
        }
        this.props.close();
    }

    /**
     * Initialize the selected combo item in each combo.
     */
    _initSelectedComboItems() {
        for (const combo of this.props.combos) {
            const comboItem = combo.selectedComboItem;
            if (comboItem) {
                this.state.selectedComboItems.set(combo.id, comboItem.deepCopy());
            }
        }
    }

    /**
     * Automatically select the single combo item in each combo that has a single, non-configurable
     * combo item.
     */
    _selectSingleComboItems() {
        for (const combo of this.props.combos) {
            const comboItem = combo.combo_items[0];
            if (combo.combo_items.length === 1 && !comboItem.product.hasNoVariantPtals) {
                this.state.selectedComboItems.set(combo.id, comboItem.deepCopy());
            }
        }
    }

    get _totalPrice() {
        const extraPrice = this.state.selectedComboItems.values().map(
            comboItem => comboItem.extra_price + comboItem.product.selectedNoVariantPtavsPriceExtra
        ).reduce((price, comboItemExtraPrice) => price + comboItemExtraPrice, 0);
        return this.state.quantity * (this.state.basePrice + extraPrice);
    }

    /**
     * Return data about the combo product.
     *
     * @return {Object} Data about the combo product.
     */
    get _comboProductData() {
        return { 'quantity': this.state.quantity };
    }

    /**
     * Return the selected combo items.
     *
     * @return {ProductComboItem[]} The selected combo items.
     */
    get _selectedComboItems() {
        return Array.from(this.state.selectedComboItems.values());
    }
}
