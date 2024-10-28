import { Component, useState } from "@odoo/owl";
import { defaultOptionComponents } from "../defaultComponents";

const alignClasses = [
    "align-items-start",
    "align-items-center",
    "align-items-end",
    "align-items-stretch",
];

export class HorizontalAlignmentOption extends Component {
    static template = "mysterious_egg.HorizontalAlignmentOption";
    static components = {
        ...defaultOptionComponents,
    };
    static props = {
        toolboxElement: Object,
    };
    setup() {
        this.state = useState(this.setState({}));
        this.env.editorBus.addEventListener("STEP_ADDED", () => {
            this.setState(this.state);
        });

        const align = this.env.editor.shared.makePreviewableOperation((id) => {
            const row = this.props.toolboxElement.querySelector(".row");
            for (const alignClass of alignClasses) {
                row.classList.remove(alignClass);
            }
            row.classList.add(id);
        });
        this.verticalAlignementButtonProps = {
            activeState: this.state,
            isActive: (buttonId, activeState) => {
                console.warn("isActive", buttonId, activeState.verticalAlignement);
                console.warn(
                    `buttonId === activeState.verticalAlignement:`,
                    buttonId === activeState.verticalAlignement
                );
                return buttonId === activeState.verticalAlignement;
            },
            onClick: (buttonId) => align.commit(buttonId),
            onMouseenter: (buttonId) => {
                align.preview(buttonId);
            },
            onMouseleave: () => {
                align.revert();
            },
        };
    }
    setState(object) {
        return Object.assign(object, {
            verticalAlignement: this.getAlignement(),
        });
    }
    getAlignement() {
        const row = this.props.toolboxElement.querySelector(".row");
        for (const alignClass of alignClasses) {
            if (row.classList.contains(alignClass)) {
                return alignClass;
            }
        }
        return "align-items-start";
    }
}
