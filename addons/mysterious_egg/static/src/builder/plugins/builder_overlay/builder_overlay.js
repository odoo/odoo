import { Component, useRef, useState } from "@odoo/owl";
import { usePosition } from "@web/core/position/position_hook";
import { makeDraggableHook } from "@web/core/utils/draggable_hook_builder_owl";
import { pick } from "@web/core/utils/objects";

const useDraggableWithoutFollow = makeDraggableHook({
    name: "useDraggable",
    onComputeParams: ({ ctx }) => {
        ctx.followCursor = false;
    },
    onWillStartDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDragStart: ({ ctx }) => pick(ctx.current, "element"),
    onDrag: ({ ctx }) => pick(ctx.current, "element"),
    onDragEnd: ({ ctx }) => pick(ctx.current, "element"),
    onDrop: ({ ctx }) => pick(ctx.current, "element"),
});

export class BuilderOverlay extends Component {
    static template = "mysterious_egg.BuilderOverlay";
    setup() {
        this.overlay = useRef("overlay");
        this.target = this.props.target;
        this.size = useState({
            height: this.target.clientHeight,
            width: this.target.clientWidth,
        });
        this.spacingConfig = this.buildSpacingConfig();

        usePosition("root", () => this.target, {
            position: "center",
            container: () => this.props.container,
            onPositioned: this.updateOverlaySize.bind(this),
        });

        useDraggableWithoutFollow({
            ref: { el: window.document.body },
            elements: ".o_handle",
            onDragStart: ({ x, y, element }) => {
                const direction = this.getCurrentDirection(element);
                const spacingConfigIndex = this.getSpacingIndexFromTarget(direction);
                this.currentDraggable = {
                    initialX: x,
                    initialY: y,
                    direction,
                    spacingConfigIndex,
                    initialSpacingConfigIndex: spacingConfigIndex,
                };
            },
            onDrag: ({ y }) => {
                // TODO: handle x
                const spacingConfig = this.spacingConfig[this.currentDraggable.direction];
                const spacingConfigIndex = this.currentDraggable.spacingConfigIndex;
                const isLastSize = spacingConfigIndex + 1 === spacingConfig.classes.length;
                const nextSizeIndex = isLastSize ? spacingConfigIndex : spacingConfigIndex + 1;
                const prevSizeIndex = spacingConfigIndex ? spacingConfigIndex - 1 : 0;
                const deltaY =
                    y -
                    this.currentDraggable.initialY +
                    spacingConfig.values[this.currentDraggable.initialSpacingConfigIndex];
                let indexToApply;

                // If the mouse moved to the right/down by at least 2/3 of
                // the space between the previous and the next steps, the
                // handle is snapped to the next step and the class is
                // replaced by the one matching this step.
                if (
                    deltaY >
                    (2 * spacingConfig.values[nextSizeIndex] +
                        spacingConfig.values[spacingConfigIndex]) /
                        3
                ) {
                    indexToApply = nextSizeIndex;
                }

                // Same as above but to the left/up.
                if (
                    deltaY <
                    (2 * spacingConfig.values[prevSizeIndex] +
                        spacingConfig.values[spacingConfigIndex]) /
                        3
                ) {
                    indexToApply = prevSizeIndex;
                }

                if (indexToApply) {
                    this.props.target.classList.remove(spacingConfig.classes[spacingConfigIndex]);
                    this.props.target.classList.add(spacingConfig.classes[indexToApply]);
                    this.currentDraggable.spacingConfigIndex = indexToApply;
                    this.updateOverlaySize();
                }
            },
        });
    }

    updateOverlaySize() {
        this.size.height = this.target.clientHeight;
        this.size.width = this.target.clientWidth;
        this.size.paddingBottom = window
            .getComputedStyle(this.target)
            .getPropertyValue("padding-bottom");
        this.size.paddingTop = window.getComputedStyle(this.target).getPropertyValue("padding-top");
    }

    buildSpacingConfig() {
        let topClass = "pt";
        let topStyleName = "padding-top";
        let bottomClass = "pb";
        let bottomStyleName = "padding-bottom";

        if (this.target.tagName === "HR") {
            topClass = "mt";
            topStyleName = "margin-top";
            bottomClass = "mb";
            bottomStyleName = "margin-bottom";
        }

        const values = [0, 4];
        for (let i = 1; i <= 256 / 8; i++) {
            values.push(i * 8);
        }

        return {
            top: { classes: values.map((v) => topClass + v), values, styleName: topStyleName },
            bottom: {
                classes: values.map((v) => bottomClass + v),
                values,
                styleName: bottomStyleName,
            },
        };
    }

    getSpacingIndexFromTarget(direction) {
        // Find the index of the current padding class applied to the target
        const spacingConfig = this.spacingConfig[direction];
        const styleName = spacingConfig.styleName;
        for (let i = 0; i < spacingConfig.classes.length; i++) {
            const paddingClass = spacingConfig.classes[i];
            const paddingValue = spacingConfig.values[i];
            if (
                this.target.classList.contains(paddingClass) ||
                window.getComputedStyle(this.target).getPropertyValue(styleName) ===
                    paddingValue + "px"
            ) {
                return i;
            }
        }
    }

    getCurrentDirection(handleElement) {
        const handleClasses = handleElement.classList;
        if (handleClasses.contains("top")) {
            return "top";
        } else if (handleClasses.contains("bottom")) {
            return "bottom";
        } else if (handleClasses.contains("end")) {
            return "end";
        } else if (handleClasses.contains("start")) {
            return "start";
        } else {
            return "";
        }
    }
}
