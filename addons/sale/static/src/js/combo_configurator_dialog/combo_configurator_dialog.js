import { useState, useSubEnv } from "@web/owl2/utils";
import { Component } from '@odoo/owl';
import { formatCurrency } from '@web/core/currency';
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from '@web/core/l10n/translation';
import { rpc } from '@web/core/network/rpc';
import { useService } from '@web/core/utils/hooks';
import { ProductCombo } from '../models/product_combo';
import { ProductTemplateAttributeLine } from '../models/product_template_attribute_line';
import { ProductCard } from '../product_card/product_card';
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
        currency_id: Number,
        company_id: { type: Number, optional: true },
        pricelist_id: { type: Number, optional: true },
        date: String,
        price_info: { type: String, optional: true },
        edit: { type: Boolean, optional: true },
        options: {
            type: Object,
            optional: true,
            shape: {
                showQuantity : { type: Boolean, optional: true },
                showPrice : { type: Boolean, optional: true },
            },
        },
        save: Function,
        discard: Function,
        close: Function,
    };

    setup() {
        this.dialog = useService('dialog');
        this.env.dialogData.dismiss = !this.props.edit && this.props.discard.bind(this);
        this.state = useState({
            // Maps combo item ids to selected combo items.
            // Note that selected combo items can be modified (i.e. their `no_variant` PTAVs can be
            // updated), so this map stores deep copies to avoid modifying the props.
            selectedComboItems: new Map(),
            // Maps combo item ids to selected quantities.
            selectedComboItemQuantities: new Map(),
            quantity: this.props.quantity,
            basePrice: this.props.price,
            isLoading: false,
        });
        this._initSelectedComboItems();
        this.getPriceUrl = '/sale/combo_configurator/get_price';
        useSubEnv({ currency: { id: this.props.currency_id } });

        this.unconfigurableCombos = this.props.combos.filter(combo => !combo.isConfigurable);
        this.configurableCombos = this.props.combos.filter(combo => combo.isConfigurable);
    }

    /**
     * Select the provided combo item, and open the product configurator iff the combo item's
     * product is configurable.
     *
     * @param {ProductCombo} combo The combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item to select.
     */
    async selectComboItem(combo, comboItem) {
        const comboId = combo.id;
        let selectedQty = this.getComboItemQuantity(comboItem.id);
        if (combo.qty_free === 1 && !selectedQty && this.totalQuantityForCombo(comboId) >= 1) {
            this.clearComboSelection(combo);
            selectedQty = this.getComboItemQuantity(comboItem.id);
        }
        // Use up-to-date selected PTAVs and custom values to populate the product configurator.
        comboItem = this.getSelectedOrProvidedComboItem(comboItem);
        let product = comboItem.product;
        if (comboItem.is_configurable) {
            if (selectedQty > 0 && this.totalQuantityForCombo(comboId) < combo.qty_free) {
                return this.setComboItemQuantity(combo, comboItem, selectedQty + 1);
            }
            this.dialog.add(ProductConfiguratorDialog, {
                productTemplateId: product.product_tmpl_id,
                ptavIds: product.selectedPtavIds,
                customPtavs: product.selectedCustomPtavs,
                quantity: 1,
                companyId: this.props.company_id,
                pricelistId: this.props.pricelist_id,
                currencyId: this.props.currency_id,
                soDate: this.props.date,
                edit: true, // Hide the optional products, if any.
                options: {
                    canChangeVariant: false,
                    showQuantity: false,
                    showPrice: false,
                    showPackaging: false,
                },
                size: "md",
                save: async configuredProduct => {
                    const selectedComboItem = comboItem.deepCopy();
                    selectedComboItem.product.ptals = configuredProduct.attribute_lines.map(
                        ProductTemplateAttributeLine.fromProductConfiguratorPtal
                    );
                    this.state.selectedComboItems.set(comboItem.id, selectedComboItem);
                    this.state.selectedComboItemQuantities.set(comboItem.id, selectedQty || 1);
                },
                discard: () => {},
                ...this._getAdditionalDialogProps(),
            });
        } else {
            this.setComboItemQuantity(combo, comboItem, selectedQty + 1);
        }
    }

    /**
     * Sets the quantity of this combo product.
     *
     * @param {Number} quantity The new quantity of this combo product.
     */
    async setQuantity(quantity) {
        if (quantity <= 0) quantity = 1;
        this.state.quantity = quantity;
        this.state.basePrice = await rpc(this.getPriceUrl, {
            product_tmpl_id: this.props.product_tmpl_id,
            currency_id: this.props.currency_id,
            quantity: quantity,
            date: this.props.date,
            company_id: this.props.company_id,
            pricelist_id: this.props.pricelist_id,
            ...this._getAdditionalRpcParams(),
        });
    }

    /**
     * Return the selected or provided combo item.
     *
     * If the provided combo item was already selected, then it may contain stale data (i.e.
     * selected PTAVs, custom values), and we should rely on the data in `state.selectedComboItems`
     * instead. Otherwise, the data in the provided combo item is up-to-date and can be used.
     *
     * @param {ProductComboItem} comboItem The provided combo item.
     * @return {ProductComboItem} The selected or provided combo item.
     */
    getSelectedOrProvidedComboItem(comboItem) {
        return this.state.selectedComboItems.get(comboItem.id) || comboItem;
    }

    /**
     * Return the selected quantity of the provided combo item.
     *
     * @param {Number} comboItemId The combo item id.
     * @return {Number} The selected quantity.
     */
    getComboItemQuantity(comboItemId) {
        return this.state.selectedComboItemQuantities.get(comboItemId) || 0;
    }

    /**
     * Set the selected quantity of the provided combo item.
     *
     * @param {ProductCombo} combo The combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item.
     * @param {Number} quantity The new quantity.
     * @return {Boolean} Whether the quantity was updated.
     */
    setComboItemQuantity(combo, comboItem, quantity) {
        const comboId = combo.id;
        const currentQty = this.getComboItemQuantity(comboItem.id);
        const maxQtyAvailable = combo.qty_free - this.totalQuantityForCombo(comboId) + currentQty;
        quantity = Math.floor(quantity || 0);
        quantity = Math.max(0, Math.min(quantity, maxQtyAvailable));
        if (quantity === currentQty) {
            return false;
        }
        if (quantity === 0) {
            this.state.selectedComboItemQuantities.delete(comboItem.id);
            this.state.selectedComboItems.delete(comboItem.id);
        } else {
            this.state.selectedComboItemQuantities.set(comboItem.id, quantity);
            this.state.selectedComboItems.set(
                comboItem.id,
                this.getSelectedOrProvidedComboItem(comboItem)
            );
        }
        return true;
    }

    /**
     * Return the total selected quantity for the provided combo.
     *
     * @param {Number} comboId The combo id.
     * @return {Number} The total selected quantity for this combo.
     */
    totalQuantityForCombo(comboId) {
        const combo = this.props.combos.find(combo => combo.id === comboId);
        return combo?.combo_items.reduce(
            (totalQty, comboItem) => totalQty + this.getComboItemQuantity(comboItem.id),
            0,
        ) || 0;
    }

    /**
     * Clear all selected items for the provided combo.
     *
     * @param {ProductCombo} combo The combo.
     */
    clearComboSelection(combo) {
        for (const comboItem of combo.combo_items) {
            this.state.selectedComboItemQuantities.delete(comboItem.id);
            this.state.selectedComboItems.delete(comboItem.id);
        }
    }

    /**
     * Check whether quantity buttons should be displayed for the provided combo item.
     *
     * @param {ProductCombo} combo The combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item.
     * @return {Boolean} Whether quantity buttons should be shown.
     */
    showQuantityButtons(combo, comboItem) {
        return this.getComboItemQuantity(comboItem.id) > 0 && combo.qty_free > 1;
    }

    get totalMessage() {
        return _t("Total: %s", this.formattedTotalPrice);
    }

    /**
     * Return the selected quantity for the provided combo.
     *
     * @param {Number} comboId The combo id.
     * @return {Number} The selected quantity for this combo.
     */
    getSelectedComboItemsCount(comboId) {
        return this.totalQuantityForCombo(comboId);
    }

    /**
     * Return the selected quantity text for the provided combo.
     *
     * @param {ProductCombo} combo The combo.
     * @return {String} The selected quantity text.
     */
    getSelectedComboItemsText(combo) {
        const selectedQty = this.getSelectedComboItemsCount(combo.id);
        return `${Math.min(selectedQty, combo.qty_free)}/${combo.qty_free}`;
    }

    /**
     * Return the total price for all units, formatted using the provided currency.
     *
     * @return {String} The formatted total price.
     */
    get formattedTotalPrice() {
        return formatCurrency(this.state.quantity * this._comboPrice, this.props.currency_id);
    }

    /**
     * Check whether a combo item has been selected for each combo.
     *
     * @return {Boolean} Whether a combo item has been selected for each combo.
     */
    get areAllCombosSelected() {
        return this.props.combos.every(
            combo => this.totalQuantityForCombo(combo.id) >= combo.qty_free
        );
    }

    async confirm(options) {
        this.state.isLoading = true;
        await this.props.save(this._comboProductData, this._selectedComboItems, options).finally(
            () => this.state.isLoading = false
        )
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
            for (const comboItem of combo.combo_items) {
                if (comboItem.selected_qty > 0) {
                    this.state.selectedComboItems.set(comboItem.id, comboItem.deepCopy());
                    this.state.selectedComboItemQuantities.set(comboItem.id, comboItem.selected_qty);
                }
            }
        }
    }

    /**
     * Return the total price per unit.
     *
     * The total price is the sum of:
     * - The combo product's price,
     * - The selected combo items' extra price,
     * - The selected `no_variant` attributes' extra price.
     *
     * @return {Number} The total price.
     */
    get _comboPrice() {
        const extraPrice = Array.from(this.state.selectedComboItemQuantities.entries()).reduce(
            (price, [comboItemId, quantity]) =>
                price + (this.state.selectedComboItems.get(comboItemId)?.totalExtraPrice || 0) * quantity,
            0,
        );
        return this.state.basePrice + extraPrice;
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
     * Return the selected combo items, in the same order as the combos given as props.
     *
     * @return {ProductComboItem[]} The sorted selected combo items.
     */
    get _selectedComboItems() {
        const selectedItems = [];
        for (const combo of this.props.combos) {
            for (const comboItem of combo.combo_items) {
                const selectedQty = this.getComboItemQuantity(comboItem.id);
                if (!selectedQty) {
                    continue;
                }
                const selectedComboItem = this.getSelectedOrProvidedComboItem(comboItem).deepCopy();
                selectedComboItem.selected_qty = selectedQty;
                selectedItems.push(selectedComboItem);
            }
        }
        return selectedItems;
    }

    /**
     * Hook to append additional RPC params in overriding modules.
     *
     * @return {Object} The additional RPC params.
     */
    _getAdditionalRpcParams() {
        return {};
    }

    /**
     * Hook to append additional props in overriding modules.
     *
     * @return {Object} The additional props.
     */
    _getAdditionalDialogProps() {
        return {};
    }
}
