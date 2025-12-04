import { Component, onMounted, onWillPatch, useRef, useState } from "@odoo/owl";
import { setElementTransform } from "@pos_restaurant/app/services/floor_plan/utils/utils";
import { computeRotationHandlePosition } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/handles/utils";
const HANDLE_OFFSET = 5;

export class Handles extends Component {
    static template = "pos_restaurant.floor_editor.handle_overlay";

    static props = {
        onStartResize: { type: Function, optional: true },
        onStartMove: { type: Function, optional: true },
        onStartRotate: { type: Function, optional: true },
        onEdit: { type: Function, optional: true },
        floorElement: { optional: true },
        canvasRef: { type: Object },
        actions: { type: Function, optional: true },
        actionMenuPosition: { type: String, optional: true },
    };

    get el() {
        return this.root.el;
    }

    setup() {
        this.root = useRef("handles");
        this.startResize = this.startResize.bind(this);

        this.state = useState({
            rotationHandlePosition: null,
        });
        onMounted(() => {
            this.updateStyle();
            this.initActionHandler();
        });
        onWillPatch(() => {
            this.updateStyle();
        });
    }

    initActionHandler() {
        const { actions } = this.props;
        if (!actions) {
            return;
        }

        actions({
            startAction: (actionType) => {
                if (this.currentAction) {
                    return;
                }
                this.currentAction = actionType;
                this.el.classList.add("action-" + actionType);
            },
            follow: (opts) => {
                this.setStyle(opts);
            },
            endAction: () => {
                const actionClass = "action-" + this.currentAction;
                // Prevent brief mispositioning of the rotation handle
                setTimeout(() => this.el.classList.remove(actionClass));
                this.currentAction = null;
            },
        });
    }

    updateStyle() {
        const { floorElement, canvasRef } = this.props;
        if (!floorElement) {
            this.el.style.display = "none";
            return;
        }

        this.el.style.display = "";

        this.setStyle(floorElement);
        this.state.rotationHandlePosition = computeRotationHandlePosition(
            floorElement,
            canvasRef.el,
            this.props.actionMenuPosition
        );
    }

    setStyle({ top, left, width, height, rotation, scale }) {
        const style = this.el.style;
        const { floorElement } = this.props;
        top = top ?? floorElement.top;
        left = left ?? floorElement.left;
        width = width ?? floorElement.width;
        height = height ?? floorElement.height;
        rotation = rotation ?? floorElement.rotation;
        scale = scale ?? floorElement.scale;

        // Set transform-origin to match the element type
        if (floorElement.shape === "line") {
            style.transformOrigin = "left center";
        } else {
            style.transformOrigin = "center center";

            if (scale > 1) {
                // Calculate actual scaled dimensions and adjust position
                const scaledWidth = width * scale;
                const scaledHeight = height * scale;
                top -= (height / 2) * (scale - 1);
                left -= (width / 2) * (scale - 1);
                width = scaledWidth;
                height = scaledHeight;
            }

            width += HANDLE_OFFSET * 2;
            height += HANDLE_OFFSET * 2;
            left -= HANDLE_OFFSET;
            top -= HANDLE_OFFSET;
        }
        style.width = `${width}px`;
        style.height = `${height}px`;
        setElementTransform(this.el, left, top, rotation);
    }

    get resizeSides() {
        const element = this.props.floorElement;
        if (!element?.isSideResizeAllowed()) {
            return false;
        }
        // Hide side handles if height is too small
        return element.height >= 25;
    }

    get resizeCorners() {
        const element = this.props.floorElement;
        return element?.isCornerResizeAllowed();
    }

    get resizeLineEnds() {
        return this.props.floorElement?.isLineEndResizeAllowed?.();
    }

    get showVerticalHandles() {
        const element = this.props.floorElement;
        return element?.isVerticalResizeAllowed();
    }

    get isStrictMode() {
        return true;
    }

    startResize(event) {
        const handle = event.currentTarget;
        const position = handle.dataset.p || handle.dataset.pos;
        this.props.onStartResize?.(position, event);
    }

    startDrag(event) {
        this.props.onStartMove?.(event, this.props.floorElement?.id);
    }

    startRotate(event) {
        this.props.onStartRotate?.(event, this.props.floorElement?.id);
    }
}
