import { Dialog } from "@web/core/dialog/dialog";
import { Component, props, t } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useService } from "@web/core/utils/hooks";

export class ChoseComboPopup extends Component {
    static template = "point_of_sale.ChoseComboPopup";
    static components = { Dialog };
    props = props({
        potentialCombos: t.array(),
        close: t.function(),
        getPayload: t.function(),
    });

    setup() {
        super.setup();
        this.pos = usePos();
        this.ui = useService("ui");
    }

    get allCombos() {
        return this.props.potentialCombos.map((combo) => ({
            ...combo,
            lines: this.pos.comboSuggestion.getComboChoiceLines(combo.combinations),
        }));
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
