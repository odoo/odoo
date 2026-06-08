import { normDeg } from "@pos_restaurant/app/services/floor_plan/utils/utils";

const HANDLE_SIZE = 40; // Approximate handle size + margin
const OPPOSITES = {
    top: "bottom",
    bottom: "top",
    left: "right",
    right: "left",
};

export function computeRotationHandlePosition(floorElement, containerEl, avoidDirection) {
    if (!floorElement || !containerEl) {
        return;
    }
    const rotation = normDeg(floorElement.rotation);
    // Handle is at bottom-center pre-rotation -> 90°
    const handleAngle = (90 + rotation) % 360;
    let handleScreenSide;
    if (handleAngle >= 315 || handleAngle < 45) {
        handleScreenSide = "right";
    } else if (handleAngle >= 45 && handleAngle < 135) {
        handleScreenSide = "bottom";
    } else if (handleAngle >= 135 && handleAngle < 225) {
        handleScreenSide = "left";
    } else {
        handleScreenSide = "top";
    }
    // Check if handle would be visible
    const visibleSides = getVisibleSides(floorElement.getBounds(), containerEl);

    if (handleScreenSide === avoidDirection || !visibleSides.includes(handleScreenSide)) {
        const targetScreenSide = OPPOSITES[avoidDirection];
        const validAlternatives = visibleSides.filter((side) => side !== avoidDirection);

        if (validAlternatives.length === 0) {
            return screenToElementSide(targetScreenSide, rotation);
        } else {
            const preferredSide = validAlternatives.includes(targetScreenSide)
                ? targetScreenSide
                : validAlternatives[0];
            return screenToElementSide(preferredSide, rotation);
        }
    } else {
        return null;
    }
}

export function getVisibleSides(bounds, containerEl) {
    const containerRect = containerEl.getBoundingClientRect();
    const elementScreenLeft = bounds.left;
    const elementScreenTop = bounds.top;
    const elementScreenRight = elementScreenLeft + bounds.width;
    const elementScreenBottom = elementScreenTop + bounds.height;
    const visible = [];
    if (elementScreenTop - HANDLE_SIZE >= containerRect.top) {
        visible.push("top");
    }
    if (elementScreenBottom + HANDLE_SIZE <= containerRect.bottom) {
        visible.push("bottom");
    }
    if (elementScreenRight + HANDLE_SIZE <= containerRect.right) {
        visible.push("right");
    }
    if (elementScreenLeft - HANDLE_SIZE >= containerRect.left) {
        visible.push("left");
    }

    return visible.length > 0 ? visible : ["bottom"];
}

const SCREEN_ANGLES = { right: 0, bottom: 90, left: 180, top: 270 };

/**
 * Convert visible side on screen  to element-space side accounting for rotation
 */
export function screenToElementSide(screenSide, rotation) {
    const screenAngle = SCREEN_ANGLES[screenSide];

    const elementAngle = (screenAngle - rotation + 360) % 360;
    if (elementAngle >= 315 || elementAngle < 45) {
        return "right";
    } else if (elementAngle >= 45 && elementAngle < 135) {
        return "bottom";
    } else if (elementAngle >= 135 && elementAngle < 225) {
        return "left";
    } else {
        return "top";
    }
}
