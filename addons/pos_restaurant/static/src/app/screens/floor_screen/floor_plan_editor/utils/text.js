import { Matrix2D } from "@pos_restaurant/app/services/floor_plan/utils/bounds_calculator";

export const TEXT_MIN_WIDTH = 100;
export const TEXT_MIN_HEIGHT = 20;
export const TEXT_DEFAULT_FONT_SIZE = 20;

export function measureText(text, styles = {}, cssClass = "") {
    const temp = document.createElement("span");
    temp.className = cssClass;
    temp.style.position = "absolute";
    temp.style.width = "auto";
    temp.style.visibility = "hidden";
    Object.assign(temp.style, styles);
    temp.textContent = text;
    document.body.appendChild(temp);
    const rect = temp.getBoundingClientRect();
    const width = Math.round(rect.width);
    const height = Math.round(rect.height);
    document.body.removeChild(temp);
    return { width, height };
}

export function setTextCaretToEnd(el) {
    const range = document.createRange();
    const sel = window.getSelection();
    range.selectNodeContents(el);
    range.collapse(false);
    sel.removeAllRanges();
    sel.addRange(range);
}

export function selectAllText(el) {
    const range = document.createRange();
    const sel = window.getSelection();
    range.selectNodeContents(el);
    sel.removeAllRanges();
    sel.addRange(range);
}

export function computeTextElementSize(textEl, element) {
    textEl.getBoundingClientRect();
    const textWidth = Math.max(TEXT_MIN_WIDTH, textEl.scrollWidth);
    const textHeight = Math.max(TEXT_MIN_HEIGHT, textEl.scrollHeight);

    const rotation = element.rotation || 0;
    const scale = element.scale || 1;

    let newLeft = element.left;
    let newTop = element.top;

    // For rotated or scaled elements, adjust position to keep the visual top-left corner fixed
    if (
        (rotation !== 0 || scale !== 1) &&
        (textWidth !== element.width || textHeight !== element.height)
    ) {
        const position = calculatePositionWithFixedTopLeft({
            left: element.left,
            top: element.top,
            oldWidth: element.width,
            oldHeight: element.height,
            newWidth: textWidth,
            newHeight: textHeight,
            rotation,
            scale,
        });
        newLeft = position.left;
        newTop = position.top;
    }

    return { top: newTop, left: newLeft, width: textWidth, height: textHeight };
}

/**
 * Calculate new position for a rotated/scaled element when dimensions change,
 * keeping the visual top-left corner fixed in place.
 */
export function calculatePositionWithFixedTopLeft({
    left,
    top,
    oldWidth,
    oldHeight,
    newWidth,
    newHeight,
    rotation = 0,
    scale = 1,
}) {
    // Create transformation matrix for the OLD element
    const oldMatrix = new Matrix2D();
    oldMatrix.translate(left + oldWidth / 2, top + oldHeight / 2);
    oldMatrix.rotate(rotation);
    if (scale !== 1) {
        oldMatrix.scale(scale, scale);
    }

    // Get the visual top-left corner position in screen space
    const oldTopLeft = oldMatrix.transformPoint(-oldWidth / 2, -oldHeight / 2);

    const newMatrix = new Matrix2D();
    newMatrix.rotate(rotation);
    if (scale !== 1) {
        newMatrix.scale(scale, scale);
    }

    // Get the rotated/scaled offset from center to top-left for new dimensions
    const newLocalTopLeft = newMatrix.transformPoint(-newWidth / 2, -newHeight / 2);

    const newCenterX = oldTopLeft.x - newLocalTopLeft.x;
    const newCenterY = oldTopLeft.y - newLocalTopLeft.y;
    const newLeft = newCenterX - newWidth / 2;
    const newTop = newCenterY - newHeight / 2;

    return { left: newLeft, top: newTop };
}
