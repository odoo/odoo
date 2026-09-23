/** @odoo-module native */
import { Component, useState, useSubEnv } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { rpc } from "@web/core/network";
import { _t } from "@web/core/translation";
import { KeepLast } from "@web/core/utils/concurrency";
import { useService } from "@web/core/utils/hooks";
import { Dialog } from "@web/ui/dialog";

import { ProductCombo } from "../models/product_combo.js";
import { ProductTemplateAttributeLine } from "../models/product_template_attribute_line.js";
import { ProductCard } from "../product_card/product_card.js";
import { ProductConfiguratorDialog } from "../product_configurator_dialog/product_configurator_dialog.js";
import { QuantityButtons } from "../quantity_buttons/quantity_buttons.js";

export class ComboConfiguratorDialog extends Component {
    static template = "sale.ComboConfiguratorDialog";
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
                showQuantity: { type: Boolean, optional: true },
                showPrice: { type: Boolean, optional: true },
            },
        },
        save: Function,
        discard: Function,
        close: Function,
    };

    setup() {
        this.dialog = useService("dialog");
        this.env.dialogData.dismiss = !this.props.edit && this.props.discard.bind(this);
        this.state = useState({
            selectedComboItems: new Map(),
            quantity: this.props.quantity,
            basePrice: this.props.price,
            isLoading: false,
        });
        this._initSelectedComboItems();
        this.getPriceUrl = "/sale/combo_configurator/get_price";
        this._priceRequests = new KeepLast();
        useSubEnv({ currency: { id: this.props.currency_id } });

        this.emptyCombos = this.props.combos.filter((combo) => combo.isEmpty);
        this.unconfigurableCombos = this.props.combos.filter(
            (combo) => !combo.isEmpty && !combo.isConfigurable,
        );
        this.configurableCombos = this.props.combos.filter(
            (combo) => !combo.isEmpty && combo.isConfigurable,
        );
    }

    /**
     * @param {Number} comboId
     * @param {ProductComboItem} comboItem
     */
    async selectComboItem(comboId, comboItem) {
        comboItem = this.getSelectedOrProvidedComboItem(comboId, comboItem);
        const product = comboItem.product;
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
                edit: true,
                options: {
                    canChangeVariant: false,
                    showQuantity: false,
                    showPrice: false,
                    showPackaging: false,
                },
                size: "md",
                save: async (configuredProduct) => {
                    const selectedComboItem = comboItem.deepCopy();
                    selectedComboItem.product.ptals =
                        configuredProduct.attribute_lines.map(
                            ProductTemplateAttributeLine.fromProductConfiguratorPtal,
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

    /** @param {Number} quantity */
    async setQuantity(quantity) {
        if (quantity <= 0) {
            quantity = 1;
        }
        this.state.quantity = quantity;
        this.state.basePrice = await this._priceRequests.add(
            rpc(this.getPriceUrl, {
                product_tmpl_id: this.props.product_tmpl_id,
                currency_id: this.props.currency_id,
                quantity: quantity,
                date: this.props.date,
                company_id: this.props.company_id,
                pricelist_id: this.props.pricelist_id,
                ...this._getAdditionalRpcParams(),
            }),
        );
        return true;
    }

    /**
     * @param {Number} comboId
     * @param {ProductComboItem} comboItem
     * @return {ProductComboItem}
     */
    getSelectedOrProvidedComboItem(comboId, comboItem) {
        const selectedComboItem = this.state.selectedComboItems.get(comboId);
        const isComboItemAlreadySelected = selectedComboItem?.id === comboItem.id;
        return isComboItemAlreadySelected ? selectedComboItem : comboItem;
    }

    get totalMessage() {
        return _t("Total: %s", this.formattedTotalPrice);
    }

    /** @return {String} */
    get formattedTotalPrice() {
        return formatCurrency(
            this.state.quantity * this._comboPrice,
            this.props.currency_id,
        );
    }

    /** @return {Boolean} */
    get areAllCombosSelected() {
        return (
            this.state.selectedComboItems.size ===
            this.props.combos.length - this.emptyCombos.length
        );
    }

    async confirm(options) {
        this.state.isLoading = true;
        try {
            await this.props.save(
                this._comboProductData,
                this._selectedComboItems,
                options,
            );
        } finally {
            this.state.isLoading = false;
        }
        this.props.close();
    }

    cancel() {
        if (!this.props.edit) {
            this.props.discard();
        }
        this.props.close();
    }

    _initSelectedComboItems() {
        for (const combo of this.props.combos) {
            const comboItem = combo.selectedComboItem;
            if (comboItem) {
                this.state.selectedComboItems.set(combo.id, comboItem.deepCopy());
            }
        }
    }

    /** @return {Number} */
    get _comboPrice() {
        const extraPrice = Array.from(this.state.selectedComboItems.values()).reduce(
            (price, item) => price + item.totalExtraPrice,
            0,
        );
        return this.state.basePrice + extraPrice;
    }

    /** @return {Object} */
    get _comboProductData() {
        return { quantity: this.state.quantity };
    }

    /** @return {ProductComboItem[]} */
    get _selectedComboItems() {
        const sortedItems = new Map(
            [...this.state.selectedComboItems.entries()].sort(
                (entry1, entry2) =>
                    this.props.combos.findIndex((combo) => combo.id === entry1[0]) -
                    this.props.combos.findIndex((combo) => combo.id === entry2[0]),
            ),
        );
        return Array.from(sortedItems.values());
    }

    /** @return {Object} */
    _getAdditionalRpcParams() {
        return {};
    }

    /** @return {Object} */
    _getAdditionalDialogProps() {
        return {};
    }
}
