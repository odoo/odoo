const SNAP_THRESHOLD = 5;

export class Snapping {
    constructor(snapGuidesContainerEl, floorPlanStore, scrollContainerEl) {
        this.snapGuidesContainerEl = snapGuidesContainerEl;
        this.floorPlanStore = floorPlanStore;
        this.scrollContainerEl = scrollContainerEl;
    }

    /**
     * Find all snap candidates for the moving element
     * @param {object} floorElement - The element being moved
     * @param {object} movingBounds - Current bounds of the moving element with corners
     * @param {number} threshold - Snap threshold in pixels
     * @returns {object} { xSnaps: Array, ySnaps: Array } - Arrays of snap candidates
     */
    findAllSnaps(floorElement, movingBounds, threshold = SNAP_THRESHOLD) {
        if (!floorElement) {
            return { xSnaps: [], ySnaps: [] };
        }

        const xSnaps = [];
        const ySnaps = [];

        // Text elements only snap by center
        const movingIsText = floorElement.isText;
        let movingXValues, movingYValues;

        if (movingIsText) {
            movingXValues = [movingBounds.centerX];
            movingYValues = [movingBounds.centerY];
        } else {
            // Determine if moving element is rotated (affects which points to check)
            const movingRotated = floorElement.rotation && floorElement.rotation % 360 !== 0;
            const c = movingBounds.corners;

            // For non-rotated elements, only check left, right, center (not all 4 corners)
            // For rotated elements, check all 4 corners since they're all different
            movingXValues = movingRotated
                ? [c.topLeft.x, c.topRight.x, c.bottomLeft.x, c.bottomRight.x, movingBounds.centerX]
                : [movingBounds.left, movingBounds.right, movingBounds.centerX];

            movingYValues = movingRotated
                ? [c.topLeft.y, c.topRight.y, c.bottomLeft.y, c.bottomRight.y, movingBounds.centerY]
                : [movingBounds.top, movingBounds.bottom, movingBounds.centerY];
        }

        // Single pass through all floor elements
        this.floorPlanStore.getAllFloorElements().forEach((floorEl) => {
            if (floorEl.uuid === floorElement.uuid) {
                return;
            }

            // Only snap tables to tables, and decor to decor
            if (floorElement.isTable !== floorEl.isTable) {
                return;
            }

            const bounds = floorEl.getBounds();

            // Only consider elements visible in the viewport
            if (!this.isElementVisible(bounds)) {
                return;
            }

            // Text elements only snap by center
            const targetIsText = floorEl.isText;
            let targetXValues, targetYValues;

            if (targetIsText) {
                targetXValues = [bounds.centerX];
                targetYValues = [bounds.centerY];
            } else {
                // Check if target element is rotated
                const targetRotated = floorEl.rotation && floorEl.rotation % 360 !== 0;
                const tc = bounds.corners;

                // For non-rotated targets, only check left, right, center
                // For rotated targets, check all 4 corners
                targetXValues = targetRotated
                    ? [
                          tc.topLeft.x,
                          tc.topRight.x,
                          tc.bottomLeft.x,
                          tc.bottomRight.x,
                          bounds.centerX,
                      ]
                    : [bounds.left, bounds.right, bounds.centerX];

                targetYValues = targetRotated
                    ? [
                          tc.topLeft.y,
                          tc.topRight.y,
                          tc.bottomLeft.y,
                          tc.bottomRight.y,
                          bounds.centerY,
                      ]
                    : [bounds.top, bounds.bottom, bounds.centerY];
            }

            // Check all X-axis snaps
            for (let i = 0; i < movingXValues.length; i++) {
                const movingX = movingXValues[i];
                for (let j = 0; j < targetXValues.length; j++) {
                    const targetX = targetXValues[j];
                    const distance = Math.abs(movingX - targetX);
                    if (distance < threshold) {
                        xSnaps.push({
                            distance,
                            movingValue: movingX,
                            targetValue: targetX,
                            targetBounds: bounds,
                        });
                    }
                }
            }

            // Check all Y-axis snaps
            for (let i = 0; i < movingYValues.length; i++) {
                const movingY = movingYValues[i];
                for (let j = 0; j < targetYValues.length; j++) {
                    const targetY = targetYValues[j];
                    const distance = Math.abs(movingY - targetY);
                    if (distance < threshold) {
                        ySnaps.push({
                            distance,
                            movingValue: movingY,
                            targetValue: targetY,
                            targetBounds: bounds,
                        });
                    }
                }
            }
        });

        return { xSnaps, ySnaps };
    }

    drawGuides(xGuides, yGuides, movingBounds) {
        const snapGuides = this.snapGuidesContainerEl;
        if (!snapGuides) {
            return;
        }

        snapGuides.innerHTML = "";

        xGuides.forEach((guide) => {
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("x1", guide.x);
            line.setAttribute("x2", guide.x);

            // For vertical guides (X-axis snapping), find Y extent from bounding boxes
            // This ensures the guide spans both elements cleanly
            const y1 = Math.min(movingBounds.top, guide.targetBounds.top);
            const y2 = Math.max(movingBounds.bottom, guide.targetBounds.bottom);

            line.setAttribute("y1", "" + y1);
            line.setAttribute("y2", "" + y2);
            line.setAttribute("class", "snap-guide");
            snapGuides.appendChild(line);
        });

        yGuides.forEach((guide) => {
            const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
            line.setAttribute("y1", guide.y);
            line.setAttribute("y2", guide.y);

            // For horizontal guides (Y-axis snapping), find X extent from bounding boxes
            // This ensures the guide spans both elements cleanly
            const x1 = Math.min(movingBounds.left, guide.targetBounds.left);
            const x2 = Math.max(movingBounds.right, guide.targetBounds.right);

            line.setAttribute("x1", "" + x1);
            line.setAttribute("x2", "" + x2);
            line.setAttribute("class", "snap-guide");
            snapGuides.appendChild(line);
        });
    }

    clearGuides() {
        this.snapGuidesContainerEl.innerHTML = "";
    }

    isElementVisible(bounds) {
        if (!this.scrollContainerEl) {
            return true;
        }

        const containerRect = this.scrollContainerEl.getBoundingClientRect();
        const scrollLeft = this.scrollContainerEl.scrollLeft;
        const scrollTop = this.scrollContainerEl.scrollTop;

        const visibleLeft = scrollLeft;
        const visibleRight = scrollLeft + containerRect.width;
        const visibleTop = scrollTop;
        const visibleBottom = scrollTop + containerRect.height;

        return (
            bounds.right >= visibleLeft &&
            bounds.left <= visibleRight &&
            bounds.bottom >= visibleTop &&
            bounds.top <= visibleBottom
        );
    }
}
