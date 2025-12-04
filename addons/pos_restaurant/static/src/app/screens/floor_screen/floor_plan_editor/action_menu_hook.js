import { onMounted, useExternalListener, onWillUnmount, useRef, onPatched } from "@odoo/owl";
import { useDebounced } from "@web/core/utils/timing";
import { normDeg } from "@pos_restaurant/app/services/floor_plan/utils/utils";

const MARGIN = 26;

export function useActionMenu(refName, containerRef, getTarget, onPositionChanged) {
    const actionMenuRef = useRef(refName);
    let hidden = false;

    function hide() {
        if (hidden) {
            return;
        }
        hidden = true;
        if (actionMenuRef.el) {
            actionMenuRef.el.style.display = "none";
        }
    }

    function getRotatedCorners(floorElement, centerX, centerY, targetRect) {
        const actualWidth = floorElement.width * floorElement.scale;
        const actualHeight = floorElement.height * floorElement.scale;
        const radians = ((floorElement.rotation || 0) * Math.PI) / 180;
        const cos = Math.cos(radians);
        const sin = Math.sin(radians);

        const corners = [
            { x: -actualWidth / 2, y: -actualHeight / 2 },
            { x: actualWidth / 2, y: -actualHeight / 2 },
            { x: actualWidth / 2, y: actualHeight / 2 },
            { x: -actualWidth / 2, y: actualHeight / 2 },
        ];

        return corners
            .map((c) => ({
                x: centerX + c.x * cos - c.y * sin,
                y: centerY + c.x * sin + c.y * cos,
            }))
            .sort((a, b) => a.y - b.y);
    }

    function shouldUseCornerPositioning(rotation) {
        if (!rotation || Math.abs(rotation) <= 5) {
            return false;
        }
        const normalized = normDeg(rotation);
        return normalized % 90 !== 0 && Math.abs(normalized % 90) >= 1;
    }

    function createPositions(menuRect, useCorners, corners, centerX, centerY, bounds) {
        if (!useCorners) {
            return [
                {
                    name: "top",
                    left: centerX - menuRect.width / 2,
                    top: bounds.top - menuRect.height - MARGIN,
                },
                { name: "bottom", left: centerX - menuRect.width / 2, top: bounds.bottom + MARGIN },
                {
                    name: "left",
                    left: bounds.left - menuRect.width - MARGIN,
                    top: centerY - menuRect.height / 2,
                },
                { name: "right", left: bounds.right + MARGIN, top: centerY - menuRect.height / 2 },
            ];
        }

        const sortedByX = [...corners].sort((a, b) => a.x - b.x);
        return [
            {
                name: "top",
                left: corners[0].x - menuRect.width / 2,
                top: corners[0].y - menuRect.height - MARGIN,
            },
            { name: "bottom", left: corners[3].x - menuRect.width / 2, top: corners[3].y + MARGIN },
            {
                name: "left",
                left: sortedByX[0].x - menuRect.width - MARGIN,
                top: sortedByX[0].y - menuRect.height / 2,
            },
            {
                name: "right",
                left: sortedByX[3].x + MARGIN,
                top: sortedByX[3].y - menuRect.height / 2,
            },
        ];
    }

    function findBestPosition(positions, menuRect, viewport, targetBounds) {
        for (const pos of positions) {
            const right = pos.left + menuRect.width;
            const bottom = pos.top + menuRect.height;

            const isVisible =
                pos.left >= viewport.left &&
                right <= viewport.right &&
                pos.top >= viewport.top &&
                bottom <= viewport.bottom;
            const noOverlap =
                right < targetBounds.left ||
                pos.left > targetBounds.right ||
                bottom < targetBounds.top ||
                pos.top > targetBounds.bottom;

            if (isVisible && noOverlap) {
                return pos;
            }
        }
        return null;
    }

    function positionMenu() {
        const menuEl = actionMenuRef.el;
        const { domElement: targetEl, floorElement } = getTarget();
        if (!menuEl || !targetEl || hidden || !floorElement) {
            return;
        }

        const containerEl = containerRef.el;
        const containerRect = containerEl.getBoundingClientRect();
        const targetRect = targetEl.getBoundingClientRect();
        const menuRect = menuEl.getBoundingClientRect();

        const scrollLeft = containerEl.scrollLeft;
        const scrollTop = containerEl.scrollTop;

        const targetBounds = {
            left: targetRect.left - containerRect.left + scrollLeft,
            top: targetRect.top - containerRect.top + scrollTop,
            right: targetRect.right - containerRect.left + scrollLeft,
            bottom: targetRect.bottom - containerRect.top + scrollTop,
        };

        const centerX = (targetBounds.left + targetBounds.right) / 2;
        const centerY = (targetBounds.top + targetBounds.bottom) / 2;

        const viewport = {
            left: scrollLeft,
            right: scrollLeft + containerRect.width,
            top: scrollTop,
            bottom: scrollTop + containerRect.height,
        };

        const useCorners = shouldUseCornerPositioning(floorElement.rotation);
        const corners = useCorners
            ? getRotatedCorners(floorElement, centerX, centerY, targetRect)
            : null;

        const positions = createPositions(
            menuRect,
            useCorners,
            corners,
            centerX,
            centerY,
            targetBounds
        );
        let bestPosition = findBestPosition(positions, menuRect, viewport, targetBounds);

        // Fallback to top position
        if (!bestPosition) {
            bestPosition = positions[0];
            const left = Math.max(
                viewport.left,
                Math.min(viewport.right - menuRect.width, bestPosition.left)
            );
            const top = Math.max(
                viewport.top,
                Math.min(viewport.bottom - menuRect.height, bestPosition.top)
            );
            menuEl.style.position = "absolute";
            menuEl.style.left = `${left}px`;
            menuEl.style.top = `${top}px`;
        } else {
            menuEl.style.position = "absolute";
            menuEl.style.left = `${bestPosition.left}px`;
            menuEl.style.top = `${bestPosition.top}px`;
        }

        if (onPositionChanged) {
            onPositionChanged(bestPosition.name);
        }
    }

    const scrollDebounced = useDebounced(() => {
        positionMenu();
        if (actionMenuRef.el) {
            actionMenuRef.el.style.opacity = "1";
            actionMenuRef.el.style.pointerEvents = "auto";
        }
    }, 150);

    const handleScroll = () => {
        if (hidden) {
            return;
        }

        if (actionMenuRef.el) {
            actionMenuRef.el.style.opacity = "0";
            actionMenuRef.el.style.pointerEvents = "none";
        }

        scrollDebounced();
    };

    const handleResize = () => {
        if (!hidden) {
            positionMenu();
        }
    };

    useExternalListener(window, "resize", useDebounced(handleResize, 150));

    onMounted(() => {
        containerRef.el?.addEventListener("scroll", handleScroll);
    });

    onWillUnmount(() => {
        containerRef.el?.removeEventListener("scroll", handleScroll);
    });

    onPatched(() => {
        positionMenu();
    });

    return {
        show() {
            if (!hidden) {
                positionMenu();
                return;
            }
            hidden = false;
            if (actionMenuRef.el) {
                actionMenuRef.el.style.display = "";
            }
            positionMenu();
        },
        hide() {
            hide();
        },
        reposition() {
            positionMenu();
        },
    };
}
