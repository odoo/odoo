import { Call } from "@mail/discuss/call/common/call";
import {
    Component,
    useState,
    onMounted,
    onWillUnmount,
    useRef,
    useEffect,
    useSubEnv,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { assignDefined } from "@mail/utils/common/misc";

const SYSTRAY_H = 40;
const MIN_WIDTH = 320;
const MIN_HEIGHT = 120;
const PADDING = 5;

/**
 * Tab-limited Call PiP.
 * Serves as a backup to the browser picture-in-picture feature when not supported by the current browser.
 *
 * @deprecated: was used for browsers that do no support documentPictureInPicture web API but they now use popout window,
 * which is a better experience over the tab-limited Call PiP.
 */
export class CallPip extends Component {
    static props = [];
    static components = { Call };
    static template = "discuss.CallPip";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.pipService = useService("discuss.pip_service");
        this.rtc = useService("discuss.rtc");
        this.rootRef = useRef("root");
        useSubEnv({ pipWindow: window });

        this.position = {
            x: PADDING,
            y: PADDING,
            width: 400,
            height: 220,
        };

        this.state = useState({
            isDragging: false,
            isResizing: false,
            isHovered: false,
            resizeDirection: null,
            hasDragged: false,
        });

        this.dragState = {
            startX: 0,
            startY: 0,
            initialX: 0,
            initialY: 0,
            initialWidth: 0,
            initialHeight: 0,
        };

        this.onMouseMove = this.onMouseMove.bind(this);
        this.onMouseUp = this.onMouseUp.bind(this);
        this.onTouchMove = this.onTouchMove.bind(this);
        this.onTouchEnd = this.onTouchEnd.bind(this);

        onMounted(() => {
            document.addEventListener("mousemove", this.onMouseMove);
            document.addEventListener("mouseup", this.onMouseUp);
            document.addEventListener("touchmove", this.onTouchMove, { passive: false });
            document.addEventListener("touchend", this.onTouchEnd);
        });

        onWillUnmount(() => {
            document.removeEventListener("mousemove", this.onMouseMove);
            document.removeEventListener("mouseup", this.onMouseUp);
            document.removeEventListener("touchmove", this.onTouchMove);
            document.removeEventListener("touchend", this.onTouchEnd);
        });

        useEffect(() => {
            this.updatePosition();
        });
    }

    updatePosition(position = {}) {
        if (!this.rootRef.el) {
            return;
        }
        assignDefined(this.position, position);
        this.rootRef.el.style = `left: ${this.position.x}px; bottom: ${this.position.y}px; width: ${this.position.width}px; height: ${this.position.height}px;`;
    }

    getPointerPosition(event) {
        return event.touches?.length > 0
            ? { x: event.touches[0].clientX, y: event.touches[0].clientY }
            : { x: event.clientX, y: event.clientY };
    }

    getResizeDirection(event, pipElement) {
        const rect = pipElement.getBoundingClientRect();
        const { x, y } = this.getPointerPosition(event);

        const tolerance = 10;
        const relativeX = x - rect.left;
        const relativeY = y - rect.top;

        let direction = "";

        if (relativeY <= tolerance) {
            direction += "n";
        } else if (relativeY >= rect.height - tolerance) {
            direction += "s";
        }

        if (relativeX <= tolerance) {
            direction += "w";
        } else if (relativeX >= rect.width - tolerance) {
            direction += "e";
        }

        return direction || null;
    }

    startDragging(event) {
        if (this.state.isResizing) {
            return;
        }

        const { x, y } = this.getPointerPosition(event);

        this.state.isDragging = true;
        this.state.hasDragged = false;

        Object.assign(this.dragState, {
            startX: x,
            startY: y,
            initialX: this.position.x,
            initialY: this.position.y,
        });

        event.preventDefault();
    }

    handleDrag(event) {
        const { x, y } = this.getPointerPosition(event);
        const deltaX = this.dragState.startX - x;
        const deltaY = this.dragState.startY - y;

        if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) {
            this.state.hasDragged = true;
        }

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        let newX = this.dragState.initialX - deltaX;
        let newY = this.dragState.initialY + deltaY;

        newX = Math.max(PADDING, Math.min(newX, viewportWidth - this.position.width - PADDING));
        newY = Math.max(PADDING, Math.min(newY, viewportHeight - this.position.height - SYSTRAY_H));
        this.updatePosition({
            x: newX,
            y: newY,
        });
    }

    handleResize(event) {
        const { x, y } = this.getPointerPosition(event);
        const deltaX = x - this.dragState.startX;
        const deltaY = y - this.dragState.startY;

        if (Math.abs(deltaX) > 2 || Math.abs(deltaY) > 2) {
            this.state.hasDragged = true;
        }

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const direction = this.state.resizeDirection;

        let newWidth = this.dragState.initialWidth;
        let newHeight = this.dragState.initialHeight;
        let newX = this.dragState.initialX;
        let newY = this.dragState.initialY;

        if (direction.includes("e")) {
            newWidth = this.dragState.initialWidth + deltaX;
        }
        if (direction.includes("w")) {
            newWidth = this.dragState.initialWidth - deltaX;
            newX = this.dragState.initialX + deltaX;
        }

        if (direction.includes("s")) {
            const heightIncrease = deltaY;
            newHeight = this.dragState.initialHeight + heightIncrease;
            newY = this.dragState.initialY - heightIncrease;
        }
        if (direction.includes("n")) {
            const heightIncrease = -deltaY;
            newHeight = this.dragState.initialHeight + heightIncrease;
        }

        newWidth = Math.min(
            newWidth,
            Math.floor((viewportWidth * 2) / 3),
            viewportWidth - Math.max(newX, PADDING) - PADDING
        );
        newHeight = Math.min(newHeight, viewportHeight - Math.max(newY, PADDING) - SYSTRAY_H);
        newWidth = Math.max(MIN_WIDTH, newWidth);
        newHeight = Math.max(MIN_HEIGHT, newHeight);

        if (direction.includes("w")) {
            newX = Math.max(
                PADDING,
                this.dragState.initialX - (newWidth - this.dragState.initialWidth)
            );
        }
        if (direction.includes("s")) {
            const finalHeightChange = newHeight - this.dragState.initialHeight;
            newY = this.dragState.initialY - finalHeightChange;
        }

        newX = Math.max(PADDING, Math.min(newX, viewportWidth - newWidth - PADDING));
        newY = Math.max(PADDING, Math.min(newY, viewportHeight - newHeight - SYSTRAY_H));

        this.updatePosition({
            width: newWidth,
            height: newHeight,
            x: newX,
            y: newY,
        });
    }

    stopDragAndResize() {
        const wasDragging = this.state.isDragging || this.state.isResizing;

        Object.assign(this.state, {
            isDragging: false,
            isResizing: false,
            resizeDirection: null,
        });

        // prevents the click event from being triggered if the user was dragging or resizing
        if (wasDragging && this.state.hasDragged) {
            setTimeout(() => {
                this.state.hasDragged = false;
            }, 10);
        }
    }

    onClickCapture(event) {
        if (this.state.hasDragged) {
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            return false;
        }
    }

    closePip() {
        this.pipService.state.active = false;
    }

    onTouchStart(event) {
        if (
            event.target.closest(".o-inset") ||
            event.target.closest(".o-discuss-CallPip-resizeHandle")
        ) {
            return;
        }
        this.startDragging(event);
    }

    onPipMousedown(event) {
        const pipElement = event.currentTarget;
        const resizeDirection = this.getResizeDirection(event, pipElement);

        if (resizeDirection) {
            this.onResizeStart(event, resizeDirection);
        } else if (!event.target.closest(".o-discuss-CallPip-close")) {
            this.startDragging(event);
        }
    }

    onPipTouchstart(event) {
        const pipElement = event.currentTarget;
        const resizeDirection = this.getResizeDirection(event, pipElement);

        if (resizeDirection) {
            this.onResizeStart(event, resizeDirection);
        } else if (!event.target.closest(".o-discuss-CallPip-close")) {
            this.startDragging(event);
        }
    }

    onResizeStart(event, direction = "se") {
        const { x, y } = this.getPointerPosition(event);

        this.state.isResizing = true;
        this.state.resizeDirection = direction;
        this.state.hasDragged = false;

        Object.assign(this.dragState, {
            startX: x,
            startY: y,
            initialX: this.position.x,
            initialY: this.position.y,
            initialWidth: this.position.width,
            initialHeight: this.position.height,
        });

        event.preventDefault();
        event.stopPropagation();
    }

    onMouseMove(event) {
        if (this.state.isResizing) {
            this.handleResize(event);
        } else if (this.state.isDragging) {
            this.handleDrag(event);
        }
    }

    onTouchMove(event) {
        this.onMouseMove(event);
        if (this.state.isDragging) {
            event.preventDefault();
        }
    }

    onMouseUp() {
        this.stopDragAndResize();
    }

    onTouchEnd() {
        this.stopDragAndResize();
    }

    onMouseenter() {
        this.state.isHovered = true;
    }

    onMouseleave() {
        this.state.isHovered = false;
    }
}

export const callPipService = {
    dependencies: ["discuss.pip_service", "mail.store"],
    start() {
        registry.category("main_components").add("discuss.CallPip", { Component: CallPip });
    },
};

registry.category("services").add("discuss.call_pip", callPipService);
