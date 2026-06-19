import { Component, onMounted, props, signal, t } from "@odoo/owl";
import { PriceFormatter } from "../price_formatter/price_formatter";

export class FeedbackPaymentSummary extends Component {
    static template = "point_of_sale.FeedbackPaymentSummary";
    static components = { PriceFormatter };

    props = props({
        formattedAmount: t.string(),
        class: t.string().optional(),
        loading: t.boolean().optional(),
    });

    amountTextRef = signal(null);
    summaryContainerRef = signal(null);

    setup() {
        onMounted(() => {
            this.scaleAmountText();
        });
    }

    scaleAmountText() {
        const containerWidth = this.summaryContainerRef().offsetWidth * 0.8; // 80% of the container width to have some space on the sides
        const amountTextEl = this.amountTextRef();

        const scale = Math.min(1, containerWidth / amountTextEl.scrollWidth);
        amountTextEl.style.transform = `scale(${scale})`;
    }
}
