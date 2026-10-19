import {
    getEventCoords,
    normDeg,
    setElementTransform,
    toDeg,
    toRad,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";

const SNAP_ANGLE = 45;
const SNAP_THRESHOLD = 5; // threshold to snap to the nearest 45-degree angle

export class RotationOperation {
    constructor({ el, event, handles, floorElement }) {
        this.el = el;
        this.handles = handles;
        this.floorElement = floorElement;

        this.isLine = floorElement.shape === "line";
        this.scale = floorElement.scale || 1;
        this.baseWidth = floorElement.width;
        this.initDeg = Number(floorElement.rotation || 0);
        this.initRad = toRad(this.initDeg);

        const rect = el.getBoundingClientRect();
        this.pivotX = rect.left + rect.width / 2;
        this.pivotY = rect.top + rect.height / 2;

        const start = getEventCoords(event);
        const startMouseAngle = Math.atan2(
            start.clientY - this.pivotY,
            start.clientX - this.pivotX
        );

        this.angleOffset = this.initRad - startMouseAngle;

        if (this.isLine) {
            // line transform origin is at left-center, so we need to compute the original left/top
            const half = this.baseWidth / 2;
            this.originalPivotX = floorElement.left + half * Math.cos(this.initRad);
            this.originalPivotY = floorElement.top + half * Math.sin(this.initRad);
        }

        this.lastTotalRad = this.initRad;
        this.rafId = null;

        handles.startAction("rotate");
    }

    applyFrame(nextRad) {
        if (this.rafId) {
            return;
        }

        this.rafId = requestAnimationFrame(() => {
            this.rafId = null;

            const totalDeg = toDeg(nextRad);

            if (this.isLine) {
                const half = this.baseWidth / 2;
                const newLeft = this.originalPivotX - half * Math.cos(nextRad);
                const newTop = this.originalPivotY - half * Math.sin(nextRad);
                setElementTransform(this.el, newLeft, newTop, totalDeg);
                this.handles.follow({ left: newLeft, top: newTop, rotation: totalDeg });
            } else {
                // Non-line shapes don't change left/top; only rotation
                setElementTransform(
                    this.el,
                    this.floorElement.left,
                    this.floorElement.top,
                    totalDeg,
                    this.scale
                );
                this.handles.follow({ rotation: totalDeg });
            }
        });
    }

    onMove(e) {
        const c = getEventCoords(e);
        const mouseAngle = Math.atan2(c.clientY - this.pivotY, c.clientX - this.pivotX);
        const rawRad = mouseAngle + this.angleOffset;

        const rawDeg = toDeg(rawRad);
        let snappedDeg = snapAngle(rawDeg);

        if (this.isLine) {
            snappedDeg = Math.round(snappedDeg);
        }

        this.lastTotalRad = toRad(snappedDeg);
        this.applyFrame(this.lastTotalRad);
    }

    isStarted() {
        return true;
    }

    stop() {
        this.handles.endAction();
        const finalDeg = Math.round(normDeg(toDeg(this.lastTotalRad)));
        if (this.isLine) {
            const half = this.baseWidth / 2;
            const left = this.originalPivotX - half * Math.cos(this.lastTotalRad);
            const top = this.originalPivotY - half * Math.sin(this.lastTotalRad);
            return { rotation: finalDeg, left, top };
        }
        return { rotation: finalDeg };
    }
}

function snapAngle(degrees) {
    const normalized = normDeg(degrees);
    const nearestSnapAngle = Math.round(normalized / SNAP_ANGLE) * SNAP_ANGLE;
    const distance = Math.abs(normalized - nearestSnapAngle);
    if (distance <= SNAP_THRESHOLD) {
        return nearestSnapAngle;
    }

    return normalized;
}
