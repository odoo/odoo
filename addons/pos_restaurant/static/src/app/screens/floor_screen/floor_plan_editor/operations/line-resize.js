import {
    getEventCoords,
    normDeg,
    setElementTransform,
    toDeg,
    toRad,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";

const MIN_SIZE = 40;
const MOVE_THRESHOLD = 5; //  minimum movement before resize/rotation starts
const ROTATION_THRESHOLD = 5; // minimum movement before rotation changes
const SNAP_ANGLE = 45; // snap to 45-degree intervals (0, 45, 90, 135, 180, ...)
const SNAP_THRESHOLD = 2; //threshold to snap to the nearest 45-degree angle

export class LineResizeOperation {
    constructor({ el, floorElement, canvasEl, handles, position, event }) {
        this.el = el;
        this.handles = handles;
        this.position = position;
        this.startLeft = floorElement.left;
        this.startTop = floorElement.top;
        this.startWidth = floorElement.width;
        this.startRotation = floorElement.rotation || 0;
        this.height = floorElement.height;

        this.isDraggingEnd = position === "line-end";
        this.canvasRect = canvasEl.getBoundingClientRect();

        const leftCenterClientX = this.canvasRect.left + this.startLeft;
        const leftCenterClientY = this.canvasRect.top + this.startTop + this.height / 2;
        const startRad = toRad(this.startRotation);

        if (this.isDraggingEnd) {
            this.fixedX = leftCenterClientX;
            this.fixedY = leftCenterClientY;
        } else {
            this.fixedX = leftCenterClientX + this.startWidth * Math.cos(startRad);
            this.fixedY = leftCenterClientY + this.startWidth * Math.sin(startRad);
        }

        const startCoords = getEventCoords(event);
        this.initialMouseX = startCoords.clientX;
        this.initialMouseY = startCoords.clientY;
        this.hasMetMoveThreshold = false;
        this.hasMetRotationThreshold = false;

        this.result = {};
        this.handles?.startAction("resize-" + position);
    }

    onMove(evt) {
        const { clientX, clientY } = getEventCoords(evt);

        // Check if we've moved enough pixels to start the operation
        const totalMovement = Math.hypot(
            clientX - this.initialMouseX,
            clientY - this.initialMouseY
        );
        if (!this.hasMetMoveThreshold && totalMovement < MOVE_THRESHOLD) {
            return;
        }

        if (!this.hasMetMoveThreshold) {
            this.hasMetMoveThreshold = true;
        }

        const dx = clientX - this.fixedX;
        const dy = clientY - this.fixedY;

        const newWidth = Math.max(MIN_SIZE, Math.hypot(dx, dy));

        // Calculate rotation
        let newRotation = toDeg(Math.atan2(dy, dx));
        if (!this.isDraggingEnd) {
            newRotation += 180;
        }
        newRotation = normDeg(newRotation);

        // Apply rotation threshold - only change rotation after moving enough
        if (!this.hasMetRotationThreshold && totalMovement < ROTATION_THRESHOLD) {
            newRotation = this.startRotation;
        } else {
            this.hasMetRotationThreshold = true;
        }

        // Apply 45-degree angle snapping
        const nearestSnapAngle = Math.round(newRotation / SNAP_ANGLE) * SNAP_ANGLE;
        const distanceToSnap = Math.abs(newRotation - nearestSnapAngle);
        if (distanceToSnap <= SNAP_THRESHOLD) {
            newRotation = nearestSnapAngle;
        } else {
            newRotation = Math.round(newRotation);
        }

        const rad = toRad(newRotation);
        let leftCenterX_client, leftCenterY_client;
        if (this.isDraggingEnd) {
            leftCenterX_client = this.fixedX;
            leftCenterY_client = this.fixedY;
        } else {
            leftCenterX_client = this.fixedX - newWidth * Math.cos(rad);
            leftCenterY_client = this.fixedY - newWidth * Math.sin(rad);
        }

        const newLeft = leftCenterX_client - this.canvasRect.left;
        const newTop = leftCenterY_client - this.height / 2 - this.canvasRect.top;

        this.result = {
            left: Math.round(newLeft),
            top: Math.round(newTop),
            width: Math.round(newWidth),
            height: Math.round(this.height),
            rotation: newRotation,
        };

        this.el.style.width = `${this.result.width}px`;
        this.el.style.height = `${this.result.height}px`;
        setElementTransform(this.el, this.result.left, this.result.top, this.result.rotation);
        this.handles?.follow(this.result);
    }

    isStarted() {
        return this.hasMetMoveThreshold;
    }

    stop() {
        this.handles?.endAction();
        return this.result;
    }
}
