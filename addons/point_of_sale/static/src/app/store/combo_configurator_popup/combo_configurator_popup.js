import { Dialog } from "@web/core/dialog/dialog";
import { Component, useState, onMounted } from "@odoo/owl";
import { usePos } from "../pos_hook";
import { ProductCard } from "@point_of_sale/app/generic_components/product_card/product_card";
import { floatIsZero } from "@web/core/utils/numbers";

export class ComboConfiguratorPopup extends Component {
    static template = "point_of_sale.ComboConfiguratorPopup";
    static components = { ProductCard, Dialog };
    static props = {
        product: Object,
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.state = useState({
            combo: Object.fromEntries(this.props.product.combo_ids.map((combo) => [combo.id, 0])),
            // configuration: id of combo_line -> ProductConfiguratorPopup payload
            configuration: {},
        });

        onMounted(() => {
            this.autoSelectSingleChoices();
            if (!this.hasMultipleChoices()) {
                this.confirm();
            }
        });
    }

    shouldShowCombo(combo) {
        return (
            combo.combo_line_ids.length > 0 &&
            (combo.combo_line_ids.length > 1 || combo.combo_line_ids[0].product_id.isConfigurable())
        );
    }

    autoSelectSingleChoices() {
        this.props.product.combo_ids.forEach((combo) => {
            if (
                combo.combo_line_ids.length === 1 &&
                !combo.combo_line_ids[0].product_id.isConfigurable()
            ) {
                this.state.combo[combo.id] = combo.combo_line_ids[0].id;
            }
        });
    }

    hasMultipleChoices() {
        return this.props.product.combo_ids.some((combo) => this.shouldShowCombo(combo));
    }

    areAllCombosSelected() {
        return Object.values(this.state.combo).every((x) => Boolean(x));
    }

    formattedComboPrice(comboLine) {
        const combo_price = comboLine.combo_price;
        if (floatIsZero(combo_price)) {
            return "";
        } else {
            const product = comboLine.product_id;
            const price = this.pos.getProductPrice(product, combo_price);
            return this.env.utils.formatCurrency(price);
        }
    }

    getSelectedComboLines() {
        return Object.values(this.state.combo)
            .filter((x) => x) // we only keep the non-zero values
            .map((x) => {
                const combo_line_id = this.pos.models["pos.combo.line"].get(x);
                return {
                    combo_line_id: combo_line_id,
                    configuration: this.state.configuration[combo_line_id.id],
                };
            });
    }

    async onClickProduct({ product, combo_line }, ev) {
        if (product.isConfigurable() && product.product_template_variant_value_ids.length === 0) {
            const payload = await this.pos.openConfigurator(product);
            if (payload) {
                this.state.configuration[combo_line.id] = payload;
            } else {
                // Do not select the product if configuration popup is cancelled.
                this.state.combo[combo_line.combo_id.id] = 0;
            }
        }
    }

    getSelectedComboItems() {
        const comboItems = this.props.product.combo_ids.flatMap(
            (comboLine) => comboLine.combo_line_ids
        );

        return Object.values(this.state.combo)
            .filter((x) => x) // we only keep the non-zero values
            .map((x) => {
                const combo_item_id = comboItems.find((comboItem) => comboItem.id == x);
                return {
                    combo_item_id: combo_item_id,
                    configuration: this.state.configuration[combo_item_id.id],
                };
            });
    }

    isArchived(comboItem) {
        const product = comboItem.product_id;
        const archivedCombinations = product._archived_combinations;
        if (!archivedCombinations) {
            return false;
        }

        const productCombination = product.product_template_variant_value_ids.map(
            (ptav) => ptav.id
        );
        return archivedCombinations.some(
            (archivedCombination) =>
                JSON.stringify(archivedCombination) === JSON.stringify(productCombination)
        );
    }

    isArchivedProductSelected() {
        return this.getSelectedComboItems().some((comboItem) =>
            this.isArchived(comboItem.combo_item_id)
        );
    }

    confirm() {
        this.props.getPayload(this.getSelectedComboLines());
        this.props.close();
    }

    get showHighResolutionImages() {
        return this.pos.showHighResolutionImages;
    }
}
