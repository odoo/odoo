import { Component, useRef, useState } from "@odoo/owl";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";

export const ELEM_ID_PREFIX = "fpe-";

export class FloorPlanBase extends Component {
    setup() {
        super.setup();
        this.floorPlanStore = useFloorPlanStore();
        this.containerRef = useRef("container");
        this.canvasRef = useRef("canvas");
        this.state = useState({ canvasWidth: 0, canvasHeight: 0 });
    }

    getDOMFloorElement(uuid) {
        if (!uuid) {
            return null;
        }
        return this.canvasRef.el.querySelector(`#${ELEM_ID_PREFIX}${uuid}`);
    }

    getTableUuidFromDOMEl(element) {
        const id = element.id;
        return id.startsWith(ELEM_ID_PREFIX) ? id.slice(ELEM_ID_PREFIX.length) : id;
    }

    get selectedFloor() {
        return this.floorPlanStore.selectedFloor;
    }

    getContainerStyle() {
        if (this.floorPlanStore.isEmpty()) {
            return "";
        }

        return this.selectedFloor.getContainerStyle() || "";
    }

    getCanvasStyles() {
        const bgCssStyle = this.selectedFloor.getBackgroundStyle();
        const width = this.formatCanvasSize(this.state.canvasWidth);
        const height = this.formatCanvasSize(this.state.canvasHeight);
        return `width:${width};height:${height};${bgCssStyle}`;
    }

    formatCanvasSize(value) {
        if (value > 0) {
            return `${value}px`;
        }
        return "100%";
    }

    scrollToElement(uuid, behavior) {
        const element = this.floorPlanStore.getElementByUuid(uuid);
        if (!element) {
            return;
        }

        const bounds = element.getBounds();
        const containerRect = this.containerRef.el.getBoundingClientRect();
        const scrollLeft = this.containerRef.el.scrollLeft;
        const scrollTop = this.containerRef.el.scrollTop;

        const visibleArea = {
            left: scrollLeft,
            top: scrollTop,
            right: scrollLeft + containerRect.width,
            bottom: scrollTop + containerRect.height,
        };

        // Check if element is already fully visible
        const isVisible =
            bounds.left >= visibleArea.left &&
            bounds.left + bounds.width <= visibleArea.right &&
            bounds.top >= visibleArea.top &&
            bounds.top + bounds.height <= visibleArea.bottom;

        if (!isVisible) {
            this.containerRef.el.scrollTo({
                left: bounds.left - (containerRect.width - bounds.width) / 2,
                top: bounds.top - (containerRect.height - bounds.height) / 2,
                behavior: behavior || "smooth",
            });
        }
    }
}
