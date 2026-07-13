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
            // Map<comboId, Map<comboItemId, { quantity: Number, item: ProductComboItem }>>
            selectedItems: new Map(),
            qty: {},
            quantity: this.props.quantity,
            basePrice: this.props.price,
            isLoading: false,
        });
        for(const combo of this.props.combos){
            this.state.selectedItems.set(combo.id, new Map());
        }
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
     * Fills selectedItemsList and the quantity object in case of Edit Configuration
     *
     */
    _initSelectedComboItems() {
        for (const combo of this.props.combos) {
            const comboItems = this.state.selectedItems.get(combo.id);
            for(const comboItem of combo.selectedComboItems) {
                comboItems.set(comboItem.id, {
                    quantity: comboItem.selected_qty,
                    item: comboItem.deepCopy(),
                });
            }
        }
    }

    /**
     * Select the provided combo item, and increase it's quantity by 1
     *
     * @param {Number} comboId The id of the combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item to select.
     */
    async selectComboItem(comboId, comboItem) {
        const combo = this.props.combos.find(c => c.id === comboId);
        const currentQty = this.state.selectedItems.get(comboId).get(comboItem.id)?.quantity ?? 0;
        const targetQty = combo.qty_free === 1 ? 1 : currentQty + 1;
        await this.setItemQuantity(comboId, comboItem, targetQty);
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
        const comboItems = this.state.selectedItems.get(comboId);
        let currentQtyForItem = comboItems.get(comboItem.id)?.quantity ?? 0;

        if (combo.qty_free === 1 && quantity > 0) {
            // Only one item can be selected at a time for this combo: selecting a
            // new one clears whatever was previously selected.
            comboItems.clear();
            currentQtyForItem = 0;
        }
        const currentTotalForCombo = this.totalQuantityForCombo(comboId);
        const maxAvailable = combo.qty_free - currentTotalForCombo + currentQtyForItem;
        const newQty = Math.max(0, Math.min(quantity, maxAvailable));

        if (
            newQty > currentQtyForItem
            && currentQtyForItem === 0
            && comboItem.is_configurable
            && !configuredItem
        ) {
            await this.handleConfigurableItem(comboId, comboItem);
            return;
        }

        if (newQty === 0) {
            comboItems.delete(comboItem.id);
        } else {
            // Reuse the already-configured item (e.g. selected PTAVs) if there is
            // one, so that increasing the quantity doesn't lose the configuration.
            const item = configuredItem || comboItems.get(comboItem.id)?.item || comboItem;
            comboItems.set(comboItem.id, { quantity: newQty, item });
        }
    }

    /**
     * Opens the configurator for a combo item and adds one quantity of the configured variant to the combo.
     *
     * @param {Number} comboId The id of the sub-combo
     * @param {ProductComboItem} comboItem The combo item to configure and add.
     */
    async handleConfigurableItem(comboId, comboItem) {
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
                const currentQty = this.state.selectedItems.get(comboId).get(comboItem.id)?.quantity ?? 0;
                await this.setItemQuantity(comboId, comboItem, currentQty + 1, selectedComboItem);
            },
            discard: () => {},
            ...this._getAdditionalDialogProps(),
        });
    }

    /**
     * Returns the total amount of selected products inside this specific sub-combo
     *
     * @param {Number} comboId The id of the sub-combo to be checked
     */
    totalQuantityForCombo(comboId) {
        let total = 0;
        for (const { quantity } of this.state.selectedItems.get(comboId).values()) {
            total += quantity;
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
        return `${this.totalQuantityForCombo(combo.id)}/${combo.qty_free}`;
    }

    /**
     * Returns the quantity currently selected for a specific combo item.
     *
     * Intended to be used from the template in place of the old
     * `state.qty[comboId][comboItemId]` lookup.
     *
     * @param {Number} comboId The id of the sub-combo.
     * @param {Number} comboItemId The id of the combo item.
     * @return {Number} The selected quantity, or 0 if not selected.
     */
    getItemQuantity(comboId, comboItemId) {
        return this.state.selectedItems.get(comboId)?.get(comboItemId)?.quantity ?? 0;
    }

    /**
     * Return the selected item for a combo item, falling back to the item as
     * provided by the combo definition if nothing is selected yet.
     * Intended for use from the template.
     *
     * @param {Number} comboId
     * @param {ProductComboItem} comboItem
     * @return {ProductComboItem}
     */
    getSelectedOrProvidedComboItem(comboId, comboItem) {
        return this.state.selectedItems.get(comboId)?.get(comboItem.id)?.item ?? comboItem;
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
        return this.props.combos.every(combo => this.totalQuantityForCombo(combo.id) === combo.qty_free);
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
        for (const comboItems of this.state.selectedItems.values()) {
            for (const { quantity, item } of comboItems.values()) {
                extraPrice += (item.totalExtraPrice || item.extra_price) * quantity;
            }
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
        for (const comboItems of this.state.selectedItems.values()) {
            for (const { quantity, item } of comboItems.values()) {
                const copy = item.deepCopy();
                copy.quantity = quantity;
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
}
