import { Component, useSubEnv } from "@odoo/owl";

export class ButtonGroup extends Component {
    static template = "mysterious_egg.ButtonGroup";
    static props = {
        activeState: { type: Object, optional: true },
        isActive: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
        onMouseenter: { type: Function, optional: true },
        onMouseleave: { type: Function, optional: true },
        slots: { type: Object, optional: true },
    };

    setup() {
        useSubEnv({
            buttonMetadatas: {
                activeState: this.props.activeState,
                isActive: this.props.isActive,
                onClick: this.props.onClick,
                onMouseenter: this.props.onMouseenter,
                onMouseleave: this.props.onMouseleave,
            },
        });
    }
}
