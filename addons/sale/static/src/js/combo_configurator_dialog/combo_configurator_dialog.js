import { Component, useState, useSubEnv } from '@odoo/owl';
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
            // Maps combo ids to selected combo items.
            // Note that selected combo items can be modified (i.e. their `no_variant` PTAVs can be
            // updated), so this map stores deep copies to avoid modifying the props.
            selectedComboItems: new Map(),
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
     * @param {Number} comboId The id of the combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item to select.
     */
    async selectComboItem(comboId, comboItem) {
        // Use up-to-date selected PTAVs and custom values to populate the product configurator.
        comboItem = this.getSelectedOrProvidedComboItem(comboId, comboItem);
        let product = comboItem.product;
        if (comboItem.is_configurable) {
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
                save: async configuredProduct => {
                    const selectedComboItem = comboItem.deepCopy();
                    selectedComboItem.product.ptals = configuredProduct.attribute_lines.map(
                        ProductTemplateAttributeLine.fromProductConfiguratorPtal
                    );
                    this.state.selectedComboItems.set(comboId, selectedComboItem);
                },
                discard: () => {},
                ...this._getAdditionalDialogProps(),
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
     * @param {Number} comboId The id of the combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The provided combo item.
     * @return {ProductComboItem} The selected or provided combo item.
     */
    getSelectedOrProvidedComboItem(comboId, comboItem) {
        const selectedComboItem = this.state.selectedComboItems.get(comboId);
        const isComboItemAlreadySelected = selectedComboItem?.id === comboItem.id;
        return isComboItemAlreadySelected ? selectedComboItem : comboItem;
    }

    get totalMessage() {
        return _t("Total: %s", this.formattedTotalPrice);
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
        return this.state.selectedComboItems.size === this.props.combos.length;
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
            const comboItem = combo.selectedComboItem;
            if (comboItem) {
                this.state.selectedComboItems.set(combo.id, comboItem.deepCopy());
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
        const extraPrice = Array.from(this.state.selectedComboItems.values()).reduce(
            (price, item) => price + item.totalExtraPrice, 0
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
        const sortedItems = new Map([...this.state.selectedComboItems.entries()].sort(
            (entry1, entry2) =>
                this.props.combos.findIndex(combo => combo.id === entry1[0])
                - this.props.combos.findIndex(combo => combo.id === entry2[0])
        ));
        return Array.from(sortedItems.values());
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
