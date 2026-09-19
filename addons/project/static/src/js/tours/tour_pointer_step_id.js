import { patch } from "@web/core/utils/patch";
import { TourInteractive } from "@web_tour/tour_interactive/tour_interactive";
import { pointerState } from "@web_tour/tour_pointer/tour_pointer";


patch(TourInteractive.prototype, {
    updatePointer() {
        super.updatePointer();
        pointerState.stepId = this.anchorEl ? this.currentAction.step.id ?? null : null;
    },
});
