/** @odoo-module */

import { Component, onWillUnmount } from "@odoo/owl";

export class ResizeHandle extends Component {
    static template = "pos_restaurant.ResizeHandle";
    static props = { onMove: Function, onMoveStart: Function, class: String, style: String };

    setup() {
        this.onMouseMove = (ev) => {
            this.onMove({ x: ev.clientX, y: ev.clientY });
        };
        this.onTouchMove = (ev) => {
            this.onMove({
                x: ev.touches[0].clientX,
                y: ev.touches[0].clientY,
            });
        };
        onWillUnmount(() => {
            document.removeEventListener("mousemove", this.onMouseMove);
            document.removeEventListener("touchmove", this.onTouchMove);
        });
    }

    onMouseDown(ev) {
        this.startPosition = { x: ev.clientX, y: ev.clientY };
        this.props.onMoveStart();
        document.addEventListener("mousemove", this.onMouseMove);
        document.addEventListener(
            "mouseup",
            (ev) => {
                ev.stopPropagation();
                document.removeEventListener("mousemove", this.onMouseMove);
            },
            { once: true, capture: true }
        );
    }

    onTouchStart(ev) {
        this.startPosition = { x: ev.touches[0].clientX, y: ev.touches[0].clientY };
        this.props.onMoveStart();
        document.addEventListener("touchmove", this.onTouchMove);
        document.addEventListener(
            "touchend",
            (ev) => {
                ev.stopPropagation();
                document.removeEventListener("touchmove", this.onTouchMove);
            },
            { once: true, capture: true }
        );
    }

    /**
     * Calls the onMove props with the delta x/y since the dragging began.
     *
     * @param {{x: number, y: number}} param0 the new position of the cursor
     */
    onMove({ x, y }) {
        this.props.onMove({
            dx: x - this.startPosition.x,
            dy: y - this.startPosition.y,
        });
    }
}
