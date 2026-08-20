import { useSubEnv } from "@web/owl2/utils";
import { Component, onMounted, onWillUnmount, proxy } from '@odoo/owl';
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
    static components = { Dialog, ProductCard,  QuantityButtons, SubItemQuantityButtons: QuantityButtons};
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
        this.state = proxy({
            // Map<comboItemId, { comboId: Number, selected_qty: Number, item: ProductComboItem }>
            selectedItems: new Map(),
            quantity: this.props.quantity,
            basePrice: this.props.price,
            isLoading: false,
        });
        this._initSelectedComboItems();
        this.getPriceUrl = '/sale/combo_configurator/get_price';
        this.getValuesUrl = '/sale/product_configurator/get_values';
        useSubEnv({ currencyId: this.props.currency_id });

        this.unconfigurableCombos = this.props.combos.filter(combo => !combo.isConfigurable);
        this.configurableCombos = this.props.combos.filter(combo => combo.isConfigurable);

        onMounted(() => this.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:ADD"));
        onWillUnmount(() => this.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:REMOVE"));
    }

    /**
     * Populate `state.selectedItems` from the combos' already-selected (or preselected)
     * combo items, e.g. when editing an existing configuration or opening a combo with
     * a single, auto-preselected choice.
     */
    _initSelectedComboItems() {
        for (const combo of this.props.combos) {
            for (const comboItem of combo.selectedComboItems) {
                this.state.selectedItems.set(comboItem.id, {
                    comboId: combo.id,
                    selected_qty: comboItem.selected_qty,
                    item: comboItem.deepCopy(),
                });
            }
        }
    }

    /**
     * Return the [comboItemId, entry] pairs currently selected for a specific sub-combo.
     *
     * @param {Number} comboId The id of the sub-combo.
     * @return {Array} The matching [comboItemId, entry] pairs.
     */
    _entriesForCombo(comboId) {
        return [...this.state.selectedItems].filter(([, entry]) => entry.comboId === comboId);
    }

    /**
     * Select the provided combo item, and increase it's quantity by 1
     *
     * @param {ProductCombo} combo The combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item to select.
     */
    async selectComboItem(combo, comboItem) {
        const currentQuantity = this.getItemQuantity(comboItem.id);
        const targetQuantity = currentQuantity + 1;
        await this.setItemQuantity(combo.id, comboItem, targetQuantity);
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
     * Sets the quantity of a specific combo item.
     *
     * @param {Number} comboId The id of the sub-combo
     * @param {ProductComboItem} comboItem The combo item to set the quantity.
     * @param {Number} quantity The new quantity to be assigned to the item
     * @param {ProductComboItem} configuredItem The combo item to set the quantity with the configuration done
     */
    async setItemQuantity(comboId, comboItem, quantity, configuredItem = null) {
        const combo = this.props.combos.find(c => c.id === comboId);

        // Preserve any existing configuration for this item before it's cleared below, so
        // that reopening the configurator for it doesn't start from a blank state.
        const previousItem = this.state.selectedItems.get(comboItem.id)?.item;

        if (combo.included_qty === 1 && quantity > 0) {
            // Only one item can be selected at a time for this combo: selecting a
            // new one clears whatever was previously selected.
            for (const [itemId] of this._entriesForCombo(comboId)) {
                this.state.selectedItems.delete(itemId);
            }
        }

        const currentItemQuantity = this.getItemQuantity(comboItem.id);
        const otherItemsQuantity = this.totalQuantityForCombo(comboId) - currentItemQuantity;
        const maxAvailable = combo.included_qty - otherItemsQuantity;
        const newQuantity = Math.max(0, Math.min(quantity, maxAvailable));

        if (newQuantity === 0) {
            this.state.selectedItems.delete(comboItem.id);
            return;
        }

        // An item that isn't in the map yet hasn't been configured: open the configurator
        // for it, unless a configuration was already provided by the caller. Reopen it with
        // its previous configuration, if any, instead of starting from a blank state.
        if (comboItem.is_configurable && !this.state.selectedItems.has(comboItem.id) && !configuredItem) {
            configuredItem = await this.handleConfigurableItem(previousItem ?? comboItem);
            if (!configuredItem) {
                return;  // The user closed the configurator without confirming.
            }
        }

        // Reuse the already-configured item (e.g. selected PTAVs) if there is one, so
        // that increasing the quantity doesn't lose the configuration.
        const item = configuredItem ?? this.state.selectedItems.get(comboItem.id)?.item ?? comboItem;
        this.state.selectedItems.set(comboItem.id, { comboId, selected_qty: newQuantity, item });
    }

    /**
     * Opens the configurator for a combo item and returns the configured item.
     *
     * @param {ProductComboItem} comboItem The combo item to configure. May already carry a
     *     previous configuration (e.g. selected PTAVs), used to prefill the dialog.
     * @return {Promise<ProductComboItem|null>} The configured combo item, or `null` if the
     *     user closed the configurator without confirming a configuration.
     */
    async handleConfigurableItem(comboItem) {
        const product = comboItem.product;

        const productConfiguratorData = await rpc(this.getValuesUrl,
            {
                product_template_id: product.product_tmpl_id,
                quantity: 1,
                currency_id: this.props.currency_id,
                so_date: this.props.date,
                company_id: this.props.company_id,
                pricelist_id: this.props.pricelist_id,
                ptav_ids:  product.selectedPtavIds,
                only_main_product: true,
                show_packaging: false,
                ...this._getAdditionalRpcParams(),
            });
        const { products } = productConfiguratorData;

        return new Promise(resolve => {
            this.dialog.add(ProductConfiguratorDialog, {
                productTemplateId: product.product_tmpl_id,
                products: products,
                optionalProducts: [],
                customPtavs: product.selectedCustomPtavs,
                companyId: this.props.company_id,
                pricelistId: this.props.pricelist_id,
                currencyId: this.props.currency_id,
                soDate: this.props.date,
                edit: true, // Hide the optional products, if any.
                options: {
                    canChangeVariant: false,
                    showQuantity: false,
                    showPrice: false,
                },
                size: "md",
                save: async configuredProduct => {
                    const selectedComboItem = comboItem.deepCopy();
                    selectedComboItem.product.ptals = configuredProduct.attribute_lines.map(
                        ProductTemplateAttributeLine.fromProductConfiguratorPtal
                    );
                    resolve(selectedComboItem);
                },
                discard: () => resolve(null),
                ...this._getAdditionalDialogProps(),
            });
        });
    }

    /**
     * Returns the total amount of selected products inside this specific sub-combo
     *
     * @param {Number} comboId The id of the sub-combo to be checked
     */
    totalQuantityForCombo(comboId) {
        let total = 0;
        for (const [, { selected_qty }] of this._entriesForCombo(comboId)) {
            total += selected_qty;
        }
        return total;
    }

    /**
     * Returns the display text representing the selected quantity for a combo.
     *
     * @param {Object} combo The sub-combo whose selected quantity text should be computed.
     * @returns {String} The formatted selected quantity text.
     */
    getSelectedComboItemsText(combo) {
        return `${this.totalQuantityForCombo(combo.id)}/${combo.included_qty}`;
    }

    /**
     * Returns the quantity currently selected for a specific combo item.
     *
     * Intended to be used from the template in place of the old
     * `state.qty[comboId][comboItemId]` lookup.
     *
     * @param {Number} comboItemId The id of the combo item.
     * @return {Number} The selected quantity, or 0 if not selected.
     */
    getItemQuantity(comboItemId) {
        return this.state.selectedItems.get(comboItemId)?.selected_qty ?? 0;
    }

    /**
     * Return the selected item for a combo item, falling back to the item as
     * provided by the combo definition if nothing is selected yet.
     * Intended for use from the template.
     *
     * @param {ProductComboItem} comboItem
     * @return {ProductComboItem}
     */
    getSelectedOrProvidedComboItem(comboItem) {
        return this.state.selectedItems.get(comboItem.id)?.item ?? comboItem;
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
        return this.props.combos.every(combo => this.totalQuantityForCombo(combo.id) === combo.included_qty);
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
        let extraPrice = 0;
        for (const { selected_qty, item } of this.state.selectedItems.values()) {
            extraPrice += item.totalExtraPrice * selected_qty;
        }
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
        const items = [];
        for (const combo of this.props.combos) {
            for (const [, { selected_qty, item }] of this._entriesForCombo(combo.id)) {
                const copy = item.deepCopy();
                copy.selected_qty = selected_qty;
                items.push(copy);
            }
        }
        return items;
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


    get allCombos() {
        return [...this.unconfigurableCombos, ...this.configurableCombos];
    }
}
