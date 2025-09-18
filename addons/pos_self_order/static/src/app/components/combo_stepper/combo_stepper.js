import { Component, onMounted, onPatched, useRef } from "@odoo/owl";

import { scrollItemIntoViewX } from "../../utils/scroll";
import { useDraggableScroll } from "../../utils/scroll_dnd_hook";
import { useHorizontalScrollShadow } from "../../utils/scroll_shadow_hook";

export class ComboStepper extends Component {
    static template = "pos_self_order.comboStepper";
    static props = ["steps", "selectedStep?", "onStepClicked"];

    setup() {
        this.containerRef = useRef("stepperContainer");
        this.scrollContainerRef = useRef("stepperScroll");
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
        scrollItemIntoViewX(
            scrollEl,
            `[data-stepper="${this.props.selectedStep.id}"]`,
            {
                edgePadding: 20,
                minRightGap: scrollEl.offsetWidth / 3,
            },
        );
    }
}
