import { Component, useState } from "@odoo/owl";
import { defaultOptionComponents } from "../defaultComponents";

export class SpacingOption extends Component {
    static template = "mysterious_egg.SpacingOption";
    static components = {
        ...defaultOptionComponents,
    };
    static props = {
        toolboxElement: Object,
    };
    setup() {
        this.target = this.props.toolboxElement.querySelector(".o_grid_mode");
        this.targetComputedStyle = getComputedStyle(this.target);

        this.state = useState(this.setState({}));
        this.env.editorBus.addEventListener("STEP_ADDED", () => {
            this.setState(this.state);
        });
        this.layoutButtonsProps = {
            activeState: this.state,
            isActive: (button, activeState) => button.id === activeState.elementLayout,
        };
    }
    setState(object) {
        Object.assign(object, {
            spacingX: parseInt(this.targetComputedStyle.columnGap),
            spacingY: parseInt(this.targetComputedStyle.rowGap),
        });
        return object;
    }
    previewSpacingX(spacing) {
        this.target.style["column-gap"] = `${spacing}px`;
    }
    previewSpacingY(spacing) {
        this.target.style["row-gap"] = `${spacing}px`;
    }
    changeSpacingX(spacing) {
        this.target.style["column-gap"] = `${spacing}px`;
        this.env.editor.dispatch("ADD_STEP");
    }
    changeSpacingY(spacing) {
        this.target.style["row-gap"] = `${spacing}px`;
        this.env.editor.dispatch("ADD_STEP");
    }
}
