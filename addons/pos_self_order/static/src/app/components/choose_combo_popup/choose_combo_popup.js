import { Component, signal, props, t } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";

export class ChooseComboPopup extends Component {
    static template = "pos_self_order.ChooseComboPopup";
    props = props({
        potentialCombos: t.array(t.object()),
        close: t.function(),
        getPayload: t.function(),
        applyCombo: t.function(),
    });

    setup() {
        this.selfOrder = useSelfOrder();
        this.ui = useService("ui");
        this.potentialCombos = signal(this.props.potentialCombos);
        this.loadingComboIndex = signal(null);
        this.hasAppliedCombo = false;
    }

    get allCombos() {
        return this.potentialCombos().map((combo) => ({
            ...combo,
            lines: this.selfOrder.comboSuggestion.getComboChoiceLines(combo.combinations),
        }));
    }

    isLoading(comboIndex) {
        return this.loadingComboIndex() === comboIndex;
    }

    waitForNextPaint() {
        return new Promise((resolve) => {
            requestAnimationFrame(() => requestAnimationFrame(resolve));
        });
    }

    async confirm(combo, comboIndex) {
        if (this.loadingComboIndex() !== null) {
            return;
        }

        this.loadingComboIndex.set(comboIndex);
        try {
            await this.waitForNextPaint();
            const payload = await this.props.applyCombo(combo);
            if (payload.potentialCombos?.length) {
                this.potentialCombos.set(payload.potentialCombos);
                this.hasAppliedCombo = true;
                return;
            }
            this.props.getPayload(payload);
            this.props.close();
        } finally {
            this.loadingComboIndex.set(null);
        }
    }

    cancel() {
        if (this.loadingComboIndex() !== null) {
            return;
        }
        if (this.hasAppliedCombo) {
            this.props.getPayload({ applied: true });
        }
        this.props.close();
    }
}
