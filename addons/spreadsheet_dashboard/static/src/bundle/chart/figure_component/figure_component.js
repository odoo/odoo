import { patch } from "@web/core/utils/patch";
import { components } from "@odoo/o-spreadsheet";
import { ChartTypeSwitcherMenu } from "../chart_type_switcher/chart_type_switcher";
import { useState } from "@odoo/owl";

const { FigureComponent } = components;

FigureComponent.components = { ...FigureComponent.components, ChartTypeSwitcherMenu };
patch(FigureComponent.prototype, {
    setup() {
        super.setup();
        this.hoverState = useState({ isHovered: false });
    },
    onMouseEnter() {
        this.hoverState.isHovered = true;
    },
    onMouseLeave() {
        this.hoverState.isHovered = false;
    },
});
