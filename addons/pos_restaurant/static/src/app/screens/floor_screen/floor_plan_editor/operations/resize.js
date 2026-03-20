import {
    getEventCoords,
    setElementTransform,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";
import { computeTextElementSize } from "@pos_restaurant/app/screens/floor_screen/floor_plan_editor/utils/text";

const MIN_SIZE = 40;
const MOVEMENT_THRESHOLD = 5;

export class ResizeOperation {
    constructor({ el, position, event, handles, floorElement }) {
        this.el = el;
        this.position = position;
        this.handles = handles;

        const { clientX: startClientX, clientY: startClientY } = getEventCoords(event);
        this.startClientX = startClientX;
        this.startClientY = startClientY;

        this.baseWidth = floorElement.width;
        this.baseHeight = floorElement.height;
        this.startScale = floorElement.scale || 1;

        this.startWidth = this.baseWidth * this.startScale;
        this.startHeight = this.baseHeight * this.startScale;
        this.startX = floorElement.left;
        this.startX -= (floorElement.width / 2) * (this.startScale - 1);
        this.startY = floorElement.top;
        this.startY -= (floorElement.height / 2) * (this.startScale - 1);

        this.rotationDeg = floorElement.rotation || 0;
        const radians = (this.rotationDeg * Math.PI) / 180;
        this.cosTheta = this.rotationDeg === 0 ? 1 : Math.cos(radians);
        this.sinTheta = this.rotationDeg === 0 ? 0 : Math.sin(radians);

        this.resizeStarted = false;

        this.isTextElement = floorElement.isText;
        this.textContentEl = this.isTextElement ? el.querySelector(".o_fp_text_content") : null;
        this.isCornerHandle = position.length === 2;
        this.maintainRatio = floorElement.isResizeMaintainRatio();

        this.includesE = position.includes("e");
        this.includesW = position.includes("w");
        this.includesS = position.includes("s");
        this.includesN = position.includes("n");

        this.startElementCenterX = this.startWidth / 2;
        this.startElementCenterY = this.startHeight / 2;

        // Calculate fixed anchor point
        const fixedAnchorInElement = this.getFixedAnchorInElement(position);
        const vectorToAnchorX = fixedAnchorInElement.x - this.startElementCenterX;
        const vectorToAnchorY = fixedAnchorInElement.y - this.startElementCenterY;
        const [rotatedVectorX, rotatedVectorY] = this.elementToScreen(
            vectorToAnchorX,
            vectorToAnchorY
        );
        this.fixedAnchorScreenX = this.startX + rotatedVectorX + this.startElementCenterX;
        this.fixedAnchorScreenY = this.startY + rotatedVectorY + this.startElementCenterY;

        this.resizeResult = {};
    }

    onMove(moveEvent) {
        const { clientX, clientY } = getEventCoords(moveEvent);

        const deltaScreenX = clientX - this.startClientX;
        const deltaScreenY = clientY - this.startClientY;

        if (!this.resizeStarted) {
            const distance = Math.sqrt(deltaScreenX * deltaScreenX + deltaScreenY * deltaScreenY);
            if (distance < MOVEMENT_THRESHOLD) {
                return;
            }
            this.resizeStarted = true;
            this.handles.startAction("resize-" + this.position);
        }

        // Transform the mouse delta to the element's coordinate system
        const [deltaElementX, deltaElementY] = this.screenToElement(deltaScreenX, deltaScreenY);

        let newWidth = this.startWidth;
        let newHeight = this.startHeight;

        if (this.isCornerHandle && this.maintainRatio) {
            // Corner resize with aspect ratio maintained
            const diagonalElementX = this.includesE ? this.startWidth : -this.startWidth;
            const diagonalElementY = this.includesS ? this.startHeight : -this.startHeight;

            const [diagonalScreenX, diagonalScreenY] = this.elementToScreen(
                diagonalElementX,
                diagonalElementY
            );
            const diagonalLengthInScreen = Math.sqrt(
                diagonalScreenX * diagonalScreenX + diagonalScreenY * diagonalScreenY
            );

            const projectionLength =
                (deltaScreenX * diagonalScreenX + deltaScreenY * diagonalScreenY) /
                diagonalLengthInScreen;

            const scaleFactor = Math.max(
                MIN_SIZE / this.startWidth,
                1 + projectionLength / diagonalLengthInScreen
            );
            newWidth = this.startWidth * scaleFactor;
            newHeight = this.startHeight * scaleFactor;
        } else {
            if (this.includesE) {
                newWidth = Math.max(MIN_SIZE, this.startWidth + deltaElementX);
            }
            if (this.includesW) {
                newWidth = Math.max(MIN_SIZE, this.startWidth - deltaElementX);
            }
            if (this.includesS) {
                newHeight = Math.max(MIN_SIZE, this.startHeight + deltaElementY);
            }
            if (this.includesN) {
                newHeight = Math.max(MIN_SIZE, this.startHeight - deltaElementY);
            }
        }

        // For non-scaled elements, use the standard calculation
        const newElementCenterX = newWidth / 2;
        const newElementCenterY = newHeight / 2;
        const fixedAnchorInResized = this.getFixedAnchorInResizedElement(
            this.position,
            newWidth,
            newHeight
        );
        const vectorToAnchorNewX = fixedAnchorInResized.x - newElementCenterX;
        const vectorToAnchorNewY = fixedAnchorInResized.y - newElementCenterY;

        // Rotate to screen coordinates
        const [rotatedVectorNewX, rotatedVectorNewY] = this.elementToScreen(
            vectorToAnchorNewX,
            vectorToAnchorNewY
        );

        const newVisualX = this.fixedAnchorScreenX - (rotatedVectorNewX + newElementCenterX);
        const newVisualY = this.fixedAnchorScreenY - (rotatedVectorNewY + newElementCenterY);

        this.applyUpdate({
            screenX: newVisualX,
            screenY: newVisualY,
            width: newWidth,
            height: newHeight,
            useScale: this.isTextElement,
            isCornerHandle: this.isCornerHandle,
        });
    }

    isStarted() {
        return this.resizeStarted;
    }

    /**
     * Transform from element coordinates to screen coordinates
     */
    elementToScreen(elementX, elementY) {
        if (this.rotationDeg === 0) {
            return [elementX, elementY];
        }
        return [
            this.cosTheta * elementX - this.sinTheta * elementY,
            this.sinTheta * elementX + this.cosTheta * elementY,
        ];
    }

    /**
     * Transform from screen coordinates back to element coordinates
     */
    screenToElement(screenX, screenY) {
        if (this.rotationDeg === 0) {
            return [screenX, screenY];
        }
        return [
            this.cosTheta * screenX + this.sinTheta * screenY,
            -this.sinTheta * screenX + this.cosTheta * screenY,
        ];
    }

    /**
     * Returns the element coordinates of the fixed anchor point at the start of resize.
     */
    getFixedAnchorInElement(handlePosition) {
        switch (handlePosition) {
            case "se":
                return { x: 0, y: 0 };
            case "sw":
                return { x: this.startWidth, y: 0 };
            case "ne":
                return { x: 0, y: this.startHeight };
            case "nw":
                return { x: this.startWidth, y: this.startHeight };
            case "e":
                return { x: 0, y: this.startHeight / 2 };
            case "w":
                return { x: this.startWidth, y: this.startHeight / 2 };
            case "s":
                return { x: this.startWidth / 2, y: 0 };
            case "n":
                return { x: this.startWidth / 2, y: this.startHeight };
            default:
                return { x: 0, y: 0 };
        }
    }

    /**
     * Returns the element coordinates of the fixed anchor point with new dimensions.
     */
    getFixedAnchorInResizedElement(handlePosition, newWidth, newHeight) {
        switch (handlePosition) {
            case "se":
                return { x: 0, y: 0 };
            case "sw":
                return { x: newWidth, y: 0 };
            case "ne":
                return { x: 0, y: newHeight };
            case "nw":
                return { x: newWidth, y: newHeight };
            case "e":
                return { x: 0, y: newHeight / 2 };
            case "w":
                return { x: newWidth, y: newHeight / 2 };
            case "s":
                return { x: newWidth / 2, y: 0 };
            case "n":
                return { x: newWidth / 2, y: newHeight };
            default:
                return { x: 0, y: 0 };
        }
    }

    /**
     * Apply the calculated dimensions and position to the element
     */
    applyUpdate({ screenX, screenY, width, height, useScale, isCornerHandle }) {
        if (useScale) {
            let newScale = this.startScale;
            let newBaseWidth = this.baseWidth;
            let newBaseHeight = this.baseHeight;

            if (isCornerHandle) {
                newScale = Math.max(1, (width / this.startWidth) * this.startScale);

                // If scale hit minimum (1), recalculate position to keep element stationary
                if (newScale === 1) {
                    const centerX = this.baseWidth / 2;
                    const centerY = this.baseHeight / 2;

                    const fixedAnchor = this.getFixedAnchorInResizedElement(
                        this.position,
                        this.baseWidth,
                        this.baseHeight
                    );

                    const [rotatedX, rotatedY] = this.elementToScreen(
                        fixedAnchor.x - centerX,
                        fixedAnchor.y - centerY
                    );

                    screenX = this.fixedAnchorScreenX - (rotatedX + centerX);
                    screenY = this.fixedAnchorScreenY - (rotatedY + centerY);
                }

                if (
                    this.resizeResult.scale === newScale &&
                    this.resizeResult.left === Math.round(screenX) &&
                    this.resizeResult.top === Math.round(screenY)
                ) {
                    return;
                }
            } else {
                const newDiffWidth = (width - this.startWidth) / this.startScale;
                newBaseWidth = this.baseWidth + newDiffWidth;

                if (this.textContentEl) {
                    // Temporarily set the width to measure content height
                    this.el.style.width = `${newBaseWidth}px`;
                    this.el.style.height = "auto";

                    // For side resize, use current position (screenX/screenY) and current dimensions
                    const updatedEl = {
                        left: screenX,
                        top: screenY,
                        width: newBaseWidth,
                        height: this.baseHeight,
                        rotation: this.rotationDeg,
                        scale: 1,
                    };
                    const data = computeTextElementSize(this.textContentEl, updatedEl);

                    newBaseHeight = data.height;
                    screenX = data.left;
                    screenY = data.top;
                }

                this.resizeResult.width = Math.round(newBaseWidth);
                this.resizeResult.height = Math.round(newBaseHeight);
            }

            let internalLeft = screenX;
            let internalTop = screenY;

            if (newScale >= 1) {
                //transformation centered
                internalLeft = screenX + (newBaseWidth / 2) * (newScale - 1);
                internalTop = screenY + (newBaseHeight / 2) * (newScale - 1);
            }

            this.resizeResult.left = Math.round(internalLeft);
            this.resizeResult.top = Math.round(internalTop);
            this.resizeResult.scale = newScale;

            this.el.style.width = `${Math.round(newBaseWidth)}px`;
            this.el.style.height = `${Math.round(newBaseHeight)}px`;
            setElementTransform(
                this.el,
                this.resizeResult.left,
                this.resizeResult.top,
                this.rotationDeg,
                newScale
            );
        } else {
            // For non-scaled elements, screenX/screenY is already the logical position
            this.resizeResult.left = Math.round(screenX);
            this.resizeResult.top = Math.round(screenY);
            this.resizeResult.width = Math.round(width);
            this.resizeResult.height = Math.round(height);
            this.el.style.width = `${Math.round(this.resizeResult.width)}px`;
            this.el.style.height = `${Math.round(this.resizeResult.height)}px`;
            setElementTransform(
                this.el,
                this.resizeResult.left,
                this.resizeResult.top,
                this.rotationDeg
            );
        }
        this.handles.follow(this.resizeResult);
    }

    stop() {
        this.handles.endAction();
        return this.resizeResult;
    }
}
