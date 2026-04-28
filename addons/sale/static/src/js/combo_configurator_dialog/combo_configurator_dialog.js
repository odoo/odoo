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
            selectedItemsList: [],
            qty: {},
            quantity: this.props.quantity,
            basePrice: this.props.price,
            isLoading: false,
        });
        for(const combo of this.props.combos){
            this.state.qty[combo.id] = {};
            for(const item of combo.combo_items){
                this.state.qty[combo.id][item.id] = 0;
            }
        }
        this._initSelectedComboItems();
        this.getPriceUrl = '/sale/combo_configurator/get_price';
        useSubEnv({ currency: { id: this.props.currency_id } });

        this.unconfigurableCombos = this.props.combos.filter(combo => !combo.isConfigurable);
        this.configurableCombos = this.props.combos.filter(combo => combo.isConfigurable);

        onMounted(() => this.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:ADD"));
        onWillUnmount(() => this.env.bus.trigger("FORM-CONTROLLER:FORM-IN-DIALOG:REMOVE"));
    }

    _initSelectedComboItems() {
        for (const combo of this.props.combos) {
            const comboItem = combo.selectedComboItem;
            if (comboItem) {
                this.state.selectedItemsList.push({
                    comboId: combo.id,
                    comboItemId: comboItem.id,
                    item: comboItem.deepCopy()
                });
                this.state.qty[combo.id][comboItem.id] = 1;
            }
        }
    }

    /**
     * Select the provided combo item, and open the product configurator iff the combo item's
     * product is configurable.
     *
     * @param {Number} comboId The id of the combo to which the combo item belongs.
     * @param {ProductComboItem} comboItem The combo item to select.
     */
    async selectComboItem(comboId, comboItem) {
        const currentQty = this.state.qty[comboId][comboItem.id];
        await this.setItemQuantity(comboId, comboItem, currentQty + 1);
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

    async setItemQuantity(comboId, comboItem, quantity, configuredItem = null) {
        const combo = this.props.combos.find(c => c.id === comboId);
        let currentQty = this.state.qty[comboId][comboItem.id];
        if (combo.qty_free === 1 && quantity > 0) {
            for (const item of combo.combo_items) {
                this.state.qty[comboId][item.id] = 0;
            }
            this.state.selectedItemsList = this.state.selectedItemsList.filter(
                selection => selection.comboId !== comboId
            );
            currentQty = 0;
        }
        if (quantity > currentQty && comboItem.is_configurable && !configuredItem) {
            await this.handleConfigurableItem(comboId, comboItem);
            return;
        }
        const currentTotalForCombo = this.totalQuantityForCombo(comboId);
        const maxAvailable = combo.qty_free - currentTotalForCombo + currentQty;
        const newQty = Math.max(0, Math.min(quantity, maxAvailable));

        const qtyToBeAdded = newQty - currentQty;
        if (qtyToBeAdded > 0) {
            for (let i = 0; i < qtyToBeAdded; i++) {
                this.state.selectedItemsList.push({
                    comboId: comboId,
                    comboItemId: comboItem.id,
                    item: configuredItem ? configuredItem : comboItem.deepCopy()
                });
            }
        } else if (qtyToBeAdded < 0) {
            let removed = 0;
            for (let i = this.state.selectedItemsList.length - 1; i >= 0; i--) {
                if (this.state.selectedItemsList[i].comboItemId === comboItem.id) {
                    this.state.selectedItemsList.splice(i, 1);
                    removed++;
                    if (removed === Math.abs(qtyToBeAdded)) break;
                }
            }
        }
        this.state.qty[comboId][comboItem.id] = newQty;
    }

    async handleConfigurableItem(comboId, comboItem) {
        const product = comboItem.product;

        const configuredProduct = await new Promise(resolve => {
            this.dialog.add(ProductConfiguratorDialog, {
                productTemplateId: product.product_tmpl_id,
                ptavIds: product.selectedPtavIds,
                customPtavs: product.selectedCustomPtavs,
                quantity: 1,
                companyId: this.props.company_id,
                pricelistId: this.props.pricelist_id,
                currencyId: this.props.currency_id,
                soDate: this.props.date,
                edit: true,
                options: {
                    canChangeVariant: false,
                    showQuantity: false,
                    showPrice: false,
                    showPackaging: false,
                },
                size: "md",
                save: resolve,
                discard: () => resolve(null),
                ...this._getAdditionalDialogProps(),
            });
        });

        if (!configuredProduct) return;
        const selectedComboItem = comboItem.deepCopy();
        selectedComboItem.product.ptals = configuredProduct.attribute_lines.map(
            ProductTemplateAttributeLine.fromProductConfiguratorPtal
        );
        const currentQty = this.state.qty[comboId][comboItem.id];
        await this.setItemQuantity(comboId, comboItem, currentQty + 1, selectedComboItem);
    }

    totalQuantityForCombo(comboId) {
        return Object.values(this.state.qty[comboId]).reduce((acc, q) => acc + q, 0);
    }

    getSelectedComboItemsText(combo) {
        if (combo.qty_free > 1) {
            const currentQty = this.totalQuantityForCombo(combo.id);
            return `${Math.min(currentQty, combo.qty_free)}/${combo.qty_free}`;
        }
        return "1";
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
        const existingSelection = this.state.selectedItemsList.find(
            selection => selection.comboItemId === comboItem.id
        );
        return existingSelection ? existingSelection.item : comboItem;
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
        const extraPrice = this.state.selectedItemsList.reduce(
            (price, selection) => price + (selection.item.totalExtraPrice || selection.item.extra_price || 0), 0
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
        return this.state.selectedItemsList.map(selection => selection.item);
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
