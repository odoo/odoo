import { Component } from "@odoo/owl";
import { usePreparationDisplay } from "@pos_preparation_display/app/preparation_display_service";
import { computeFontColor } from "@pos_preparation_display/app/utils";

export class Stages extends Component {
    static template = "pos_preparation_display.Stages";
    static props = {
        stages: Object,
    };

    setup() {
        this.preparationDisplay = usePreparationDisplay();
    }

    getFontColor(bgColor) {
        return computeFontColor(bgColor);
    }
}
