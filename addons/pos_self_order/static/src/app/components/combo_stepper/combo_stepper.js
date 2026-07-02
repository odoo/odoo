import { Component, onMounted, onPatched, signal } from "@odoo/owl";
import { useHorizontalScrollShadow } from "../../utils/scroll_shadow_hook";
import { useDraggableScroll } from "../../utils/scroll_dnd_hook";
import { scrollItemIntoViewX } from "../../utils/scroll";

export class Stepper extends Component {
    static template = "pos_self_order.stepper";
    static props = ["steps", "selectedStep?", "onStepClicked"];

    setup() {
        this.containerRef = signal.ref();
        this.scrollContainerRef = signal.ref();
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
        if (!this.scrollContainerRef.el || !this.props.selectedStep) {
            return;
        }
        const scrollEl = this.scrollContainerRef.el;
        scrollItemIntoViewX(scrollEl, `[data-stepper="${this.props.selectedStep.id}"]`, {
            edgePadding: 20,
            minRightGap: scrollEl.offsetWidth / 3,
        });
    }
}
