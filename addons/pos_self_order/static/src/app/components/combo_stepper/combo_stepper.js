import { Component, onMounted, onPatched, props, signal, t } from "@odoo/owl";
import { useHorizontalScrollShadow } from "../../utils/scroll_shadow_hook";
import { useDraggableScroll } from "../../utils/scroll_dnd_hook";
import { scrollItemIntoViewX } from "../../utils/scroll";

export class Stepper extends Component {
    static template = "pos_self_order.stepper";
    props = props({
        steps: t.array(),
        selectedStep: t.object().optional(),
        onStepClicked: t.function(),
    });

    containerRef = signal(null);
    scrollContainerRef = signal(null);

    setup() {
        useHorizontalScrollShadow(this.scrollContainerRef, this.containerRef);
        useDraggableScroll(this.scrollContainerRef);

        onMounted(() => {
            this.ensureStepVisible();
        });

        onPatched(() => {
            this.ensureStepVisible();
        });
    }

    ensureStepVisible() {
        if (!this.scrollContainerRef() || !this.props.selectedStep) {
            return;
        }
        const scrollEl = this.scrollContainerRef();
        scrollItemIntoViewX(scrollEl, `[data-stepper="${this.props.selectedStep.id}"]`, {
            edgePadding: 20,
            minRightGap: scrollEl.offsetWidth / 3,
        });
    }
}
