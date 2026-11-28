import { Component, proxy, signal } from "@odoo/owl";
import { useFloorPlanStore } from "@pos_restaurant/app/hooks/floor_plan_hook";

export const ELEM_ID_PREFIX = "fpe-";

export class FloorPlanBase extends Component {
    containerRef = signal.ref();
    canvasRef = signal.ref();

    setup() {
        super.setup();
        this.floorPlanStore = useFloorPlanStore();
        this.state = proxy({ canvasWidth: 0, canvasHeight: 0 });
        this.canvasOffset = { x: 0, y: 0 };
    }

    getDOMFloorElement(uuid) {
        if (!uuid) {
            return null;
        }
        return this.canvasRef().querySelector(`#${ELEM_ID_PREFIX}${uuid}`);
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
        const { x, y } = this.canvasOffset;
        const width = this.formatCanvasSize(this.state.canvasWidth, x);
        const height = this.formatCanvasSize(this.state.canvasHeight, y);
        return `width:${width};height:${height};margin:${y}px 0 0 ${x}px;${bgCssStyle}`;
    }

    formatCanvasSize(value, offset) {
        if (value > 0) {
            return `${value}px`;
        }
        return offset > 0 ? `calc(100% - ${offset}px)` : "100%";
    }

    scrollToElement(uuid, behavior) {
        const element = this.floorPlanStore.getElementByUuid(uuid);
        if (!element) {
            return;
        }

        const bounds = element.getBounds();
        const containerRect = this.containerRef().getBoundingClientRect();
        const scrollLeft = this.containerRef().scrollLeft - this.canvasOffset.x;
        const scrollTop = this.containerRef().scrollTop - this.canvasOffset.y;

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
            this.containerRef().scrollTo({
                left: bounds.left + this.canvasOffset.x - (containerRect.width - bounds.width) / 2,
                top: bounds.top + this.canvasOffset.y - (containerRect.height - bounds.height) / 2,
                behavior: behavior || "smooth",
            });
        }
    }
}
