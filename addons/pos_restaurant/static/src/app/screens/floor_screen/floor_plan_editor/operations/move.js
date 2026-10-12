import {
    getEventCoords,
    setElementTransform,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";
import { calculateBoundsFromTransform } from "@pos_restaurant/app/services/floor_plan/utils/bounds_calculator";
import { clamp } from "@web/core/utils/numbers";

const SCROLL_ZONE = 20;
const MAX_SCROLL_SPEED = 5;
const SCROLL_ACCEL = 0.15;
const DRAG_THRESHOLD = 5; // pixels to move before starting drag
const EXPAND_PAD = 5;
const MIN_VISIBLE_SIZE = 50;
const FAST_MOVE_THRESHOLD = 15; // pixels per frame - disable snapping if moving faster

export class MoveOperation {
    constructor({ el, floorElement, event, canvasEl, scrollContainerEl, snapping, handles }) {
        this.el = el;
        this.floorElement = floorElement;
        this.floorElemGeo = this.floorElement.getGeometry();
        this.canvasEl = canvasEl;
        this.scrollContainerEl = scrollContainerEl;
        this.snapping = snapping;
        this.handles = handles;

        const coords = getEventCoords(event);
        const canvasRect = canvasEl.getBoundingClientRect();
        this.dragOffsetX = coords.clientX - canvasRect.left - this.floorElement.left;
        this.dragOffsetY = coords.clientY - canvasRect.top - this.floorElement.top;

        this.initialPointerX = this.lastPointerX = this.lastProcessedX = coords.clientX;
        this.initialPointerY = this.lastPointerY = this.lastProcessedY = coords.clientY;
        this.lastPosition = null;

        this.scrollVelocity = { x: 0, y: 0 };
        this.isEnded = false;
        this.dragStarted = false;
        this.lastMoveTime = performance.now();

        this.rafId = requestAnimationFrame(() => this.dragTick());
    }

    doMove(newLeft, newTop, skipSnapping = false) {
        this.floorElemGeo.top = Math.round(newTop);
        this.floorElemGeo.left = Math.round(newLeft);

        let bounds = calculateBoundsFromTransform(this.floorElemGeo);

        let xSnaps = [];
        let ySnaps = [];

        // Skip snapping during autoscroll or when disabled
        if (!skipSnapping && !this.ctrlPressed) {
            // Use optimized single-pass snap finding
            const snapResults = this.snapping.findAllSnaps(this.floorElement, bounds);

            // Convert snap results to the format needed for guide drawing
            // For each snap, calculate the position delta needed
            xSnaps = snapResults.xSnaps.map((snap) => ({
                distance: snap.distance,
                newLeft: newLeft + (snap.targetValue - snap.movingValue),
                newTop: newTop,
                guideLine: snap.targetValue,
                targetBounds: snap.targetBounds,
            }));

            ySnaps = snapResults.ySnaps.map((snap) => ({
                distance: snap.distance,
                newLeft: newLeft,
                newTop: newTop + (snap.targetValue - snap.movingValue),
                guideLine: snap.targetValue,
                targetBounds: snap.targetBounds,
            }));
        }

        // Apply best snap and collect guides for all close snaps
        const xGuides = [];
        const yGuides = [];

        if (xSnaps.length > 0) {
            xSnaps.sort((a, b) => a.distance - b.distance);
            newLeft = xSnaps[0].newLeft;
            xSnaps.forEach(
                (s) =>
                    Math.abs(s.distance - xSnaps[0].distance) < 0.1 &&
                    xGuides.push({ x: s.guideLine, targetBounds: s.targetBounds })
            );
        }

        if (ySnaps.length > 0) {
            ySnaps.sort((a, b) => a.distance - b.distance);
            newTop = ySnaps[0].newTop;
            ySnaps.forEach(
                (s) =>
                    Math.abs(s.distance - ySnaps[0].distance) < 0.1 &&
                    yGuides.push({ y: s.guideLine, targetBounds: s.targetBounds })
            );
        }

        if (this.floorElemGeo.top !== newTop || this.floorElemGeo.left !== newLeft) {
            this.floorElemGeo.top = newTop;
            this.floorElemGeo.left = newLeft;
            bounds = calculateBoundsFromTransform(this.floorElemGeo);
        }

        const position = constrainPositionToCanvas(newLeft, newTop, bounds, this.canvasEl);

        if (this.floorElemGeo.top !== position.top || this.floorElemGeo.left !== position.left) {
            this.floorElemGeo.top = position.top;
            this.floorElemGeo.left = position.left;
            bounds = calculateBoundsFromTransform(this.floorElemGeo);
        }

        position.left = Math.round(position.left);
        position.top = Math.round(position.top);
        this.setElementTransform(position.left, position.top);
        this.lastPosition = position;
        this.handles.follow(position);
        this.snapping.drawGuides(xGuides, yGuides, bounds);

        return bounds;
    }

    setElementTransform(left, top) {
        setElementTransform(
            this.el,
            left,
            top,
            this.floorElement.rotation,
            this.floorElement.scale
        );
    }

    isStarted() {
        return this.dragStarted && !this.isEnded;
    }

    dragTick() {
        if (this.isEnded) {
            if (this.rafId) {
                cancelAnimationFrame(this.rafId);
                this.rafId = null;
            }
            return;
        }

        this.rafId = requestAnimationFrame(() => this.dragTick());

        const pointerMoved =
            this.lastPointerX !== this.lastProcessedX || this.lastPointerY !== this.lastProcessedY;

        if (!pointerMoved && !this.dragStarted) {
            return;
        }

        // Auto-scroll calculations (run every frame for smooth acceleration/deceleration)
        const containerRect = this.scrollContainerEl.getBoundingClientRect();
        const maxScrollX = this.scrollContainerEl.scrollWidth - this.scrollContainerEl.clientWidth;
        const maxScrollY =
            this.scrollContainerEl.scrollHeight - this.scrollContainerEl.clientHeight;

        const targetVelX = calculateAutoScroll(
            this.lastPointerX,
            containerRect.left,
            containerRect.right,
            this.scrollContainerEl.scrollLeft,
            maxScrollX
        );

        const targetVelY = calculateAutoScroll(
            this.lastPointerY,
            containerRect.top,
            containerRect.bottom,
            this.scrollContainerEl.scrollTop,
            maxScrollY
        );

        this.scrollVelocity.x += (targetVelX - this.scrollVelocity.x) * SCROLL_ACCEL;
        this.scrollVelocity.y += (targetVelY - this.scrollVelocity.y) * SCROLL_ACCEL;

        let didScroll = false;
        if (Math.abs(this.scrollVelocity.x) > 0.1 || Math.abs(this.scrollVelocity.y) > 0.1) {
            this.scrollContainerEl.scrollBy({
                left: this.scrollVelocity.x,
                top: this.scrollVelocity.y,
            });
            didScroll = true;
        }

        // Update element position if pointer moved OR if we scrolled
        if (pointerMoved || didScroll) {
            // Calculate move velocity to detect fast movements
            const currentTime = performance.now();
            const timeDelta = currentTime - this.lastMoveTime;
            const dx = this.lastPointerX - this.lastProcessedX;
            const dy = this.lastPointerY - this.lastProcessedY;
            const distance = Math.sqrt(dx * dx + dy * dy);

            // Calculate speed (pixels per millisecond, normalized to 16ms frame)
            const speed = timeDelta > 0 ? (distance / timeDelta) * 16 : 0;
            const isMovingFast = speed > FAST_MOVE_THRESHOLD;

            this.lastProcessedX = this.lastPointerX;
            this.lastProcessedY = this.lastPointerY;
            this.lastMoveTime = currentTime;

            if (!this.dragStarted) {
                const startDx = this.lastPointerX - this.initialPointerX;
                const startDy = this.lastPointerY - this.initialPointerY;
                const startDistance = Math.sqrt(startDx * startDx + startDy * startDy);

                if (startDistance < DRAG_THRESHOLD) {
                    return;
                }

                this.dragStarted = true;
                this.handles.startAction("move");
            }

            const canvasRect = this.canvasEl.getBoundingClientRect();
            const newLeft = this.lastPointerX - canvasRect.left - this.dragOffsetX;
            const newTop = this.lastPointerY - canvasRect.top - this.dragOffsetY;

            // Skip snapping if moving fast, during scroll, or already skipping
            const skipSnapping = didScroll || isMovingFast;
            const bounds = this.doMove(newLeft, newTop, skipSnapping);
            expandBoard(this.canvasEl, bounds.right, bounds.bottom);
        }
    }

    onMove(event) {
        if (this.isEnded) {
            return;
        }
        const coords = getEventCoords(event);
        this.lastPointerX = coords.clientX;
        this.lastPointerY = coords.clientY;
        this.ctrlPressed = event.ctrlKey || event.metaKey;
        // The animation frame will handle starting the drag and rest
    }

    stop() {
        this.isEnded = true;
        if (this.rafId) {
            cancelAnimationFrame(this.rafId);
            this.rafId = null;
        }

        if (this.dragStarted) {
            this.handles.endAction();
            this.snapping.clearGuides();
            return this.lastPosition;
        }

        return false;
    }
}

export function constrainPositionToCanvas(logicalLeft, logicalTop, bounds, canvasEl) {
    const canvasWidth = canvasEl.offsetWidth;
    const canvasHeight = canvasEl.offsetHeight;

    const visibleWidth = Math.min(MIN_VISIBLE_SIZE, bounds.width);
    const visibleHeight = Math.min(MIN_VISIBLE_SIZE, bounds.height);

    const minBoundLeft = -(bounds.width - visibleWidth);
    const maxBoundLeft = canvasWidth - visibleWidth;
    const minBoundTop = -(bounds.height - visibleHeight);
    const maxBoundTop = canvasHeight - visibleHeight;

    const constrainedBoundLeft = clamp(bounds.left, minBoundLeft, maxBoundLeft);
    const constrainedBoundTop = clamp(bounds.top, minBoundTop, maxBoundTop);

    // Calculate the adjustment needed for the logical position
    const deltaLeft = constrainedBoundLeft - bounds.left;
    const deltaTop = constrainedBoundTop - bounds.top;

    return {
        left: logicalLeft + deltaLeft,
        top: logicalTop + deltaTop,
    };
}

export function expandBoard(canvasEl, requiredRight, requiredBottom) {
    let bw = canvasEl.clientWidth;
    let bh = canvasEl.clientHeight;

    let changed = false;

    if (requiredRight + EXPAND_PAD > bw) {
        bw = Math.ceil(requiredRight + EXPAND_PAD);
        canvasEl.style.width = bw + "px";
        changed = true;
    }

    if (requiredBottom + EXPAND_PAD > bh) {
        bh = Math.ceil(requiredBottom + EXPAND_PAD);
        canvasEl.style.height = bh + "px";
        changed = true;
    }
    return changed;
}

export function calculateAutoScroll(pointerPos, min, max, currentScroll, maxScroll) {
    const distFromStart = pointerPos - min;
    const distFromEnd = max - pointerPos;

    let targetSpeed = 0;

    if (distFromStart < SCROLL_ZONE && currentScroll > 0) {
        targetSpeed = -MAX_SCROLL_SPEED;
    } else if (distFromEnd < SCROLL_ZONE && currentScroll < maxScroll) {
        targetSpeed = MAX_SCROLL_SPEED;
    }

    return targetSpeed;
}
