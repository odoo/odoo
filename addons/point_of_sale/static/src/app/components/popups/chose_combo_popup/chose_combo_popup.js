import { Dialog } from "@web/core/dialog/dialog";
import { Component } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class ChoseComboPopup extends Component {
    static template = "point_of_sale.ChoseComboPopup";
    static components = { Dialog };
    static props = {
        potentialCombos: Object,
        close: Function,
        getPayload: Function,
    };

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
    }

    getLines(combo) {
        const comboItems = {};
        for (const [comboId, comboChoice] of Object.entries(combo)) {
            const comboProduct = this.pos.models["product.combo"].get(comboId);
            const maxQty = comboProduct.qty_max;
            const totalChosenQty = Object.values(comboChoice).reduce(
                (sum, line) => (line === true ? sum : sum + line.qty),
                0
            );
            for (const line of Object.values(comboChoice)) {
                if (line === true) {
                    // Upsell option
                    if (totalChosenQty < maxQty) {
                        // If the upsell option is already full, we do not show it as upsell
                        comboItems[comboProduct.name] = {
                            quantity: comboProduct.qty_max - totalChosenQty,
                            upsell: true,
                            sequence: comboProduct.sequence,
                            id: comboProduct.id,
                        };
                    }
                    continue;
                }
                if (!comboItems[line.combo_item.product_id.display_name]) {
                    comboItems[line.combo_item.product_id.display_name] = {
                        quantity: 0,
                        upsell: false,
                        sequence: comboProduct.sequence,
                        id: comboProduct.id,
                    };
                }
                comboItems[line.combo_item.product_id.display_name].quantity += line.qty;
            }
        }
        return Object.entries(comboItems)
            .map(([name, { quantity, upsell, sequence, id }]) => ({
                name,
                quantity,
                upsell,
                sequence,
                id,
            }))
            .sort((a, b) => {
                if (a.upsell !== b.upsell) {
                    return a.upsell ? 1 : -1;
                }
                if (a.sequence !== b.sequence) {
                    return a.sequence - b.sequence;
                }
                return a.id - b.id;
            });
    }

    get allCombos() {
        const applicableCombos = this.props.potentialCombos.applicable;
        for (const combo of applicableCombos) {
            combo.lines = this.getLines(combo.combinations[0]);
        }
        const upsellCombos = this.props.potentialCombos.upsell;
        for (const combo of upsellCombos) {
            combo.upsell = true;
            combo.lines = this.getLines(combo.combinations[0]);
        }
        return [...applicableCombos, ...upsellCombos];
    }

    get contentClass() {
        if (this.ui.isSmall) {
            return "";
        }
        return "mh-75";
    }

    confirm(combo) {
        this.props.getPayload(combo);
        this.props.close();
    }
}
