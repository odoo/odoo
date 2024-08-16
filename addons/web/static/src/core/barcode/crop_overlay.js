import { Component, useRef, onPatched } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { clamp } from "@web/core/utils/numbers";

export class CropOverlay extends Component {
    static template = "web.CropOverlay";
    static props = {
        onResize: Function,
        isReady: Boolean,
        slots: {
            type: Object,
            shape: {
                default: {},
            },
        },
    };

    setup() {
        this.localStorageKey = "o-barcode-scanner-overlay";
        this.cropContainerRef = useRef("crop-container");
        this.isMoving = false;
        this.boundaryOverlay = {};
        this.relativePosition = {
            x: 0,
            y: 0,
        };
        onPatched(() => {
            this.setupCropRect();
        });
    }

    setupCropRect() {
        if (!this.props.isReady) {
            return;
        }
        this.computeDefaultPoint();
        this.computeOverlayPosition();
        this.calculateAndSetTransparentRect();
        this.executeOnResizeCallback();
    }

    boundPoint(pointValue, boundaryRect) {
        return {
            x: clamp(pointValue.x, boundaryRect.left, boundaryRect.left + boundaryRect.width),
            y: clamp(pointValue.y, boundaryRect.top, boundaryRect.top + boundaryRect.height),
        };
    }

    calculateAndSetTransparentRect() {
        const cropTransparentRect = this.getTransparentRec(
            this.relativePosition,
            this.boundaryOverlay
        );
        this.setCropValue(cropTransparentRect, this.relativePosition);
    }

    computeOverlayPosition() {
        const cropOverlayElement = this.cropContainerRef.el.querySelector(".o_crop_overlay");
        this.boundaryOverlay = cropOverlayElement.getBoundingClientRect();
    }

    executeOnResizeCallback() {
        const transparentRec = this.getTransparentRec(this.relativePosition, this.boundaryOverlay);
        browser.localStorage.setItem(this.localStorageKey, JSON.stringify(transparentRec));
        this.props.onResize({
            ...transparentRec,
            width: this.boundaryOverlay.width - 2 * transparentRec.x,
            height: this.boundaryOverlay.height - 2 * transparentRec.y,
        });
    }

    computeDefaultPoint() {
        const firstChildComputedStyle = getComputedStyle(this.cropContainerRef.el.firstChild);
        const elementWidth = firstChildComputedStyle.width.slice(0, -2);
        const elementHeight = firstChildComputedStyle.height.slice(0, -2);

        const stringSavedPoint = browser.localStorage.getItem(this.localStorageKey);
        if (stringSavedPoint) {
            const savedPoint = JSON.parse(stringSavedPoint);
            this.relativePosition = {
                x: clamp(savedPoint.x, 0, elementWidth),
                y: clamp(savedPoint.y, 0, elementHeight),
            };
        } else {
            const stepWidth = elementWidth / 10;
            const width = stepWidth * 8;
            const height = width / 4;
            const startY = elementHeight / 2 - height / 2;
            this.relativePosition = {
                x: stepWidth + width,
                y: startY + height,
            };
        }
    }
    getTransparentRec(point, rect) {
        const middleX = rect.width / 2;
        const middleY = rect.height / 2;
        const newDeltaX = Math.abs(point.x - middleX);
        const newDeltaY = Math.abs(point.y - middleY);
        return {
            x: middleX - newDeltaX,
            y: middleY - newDeltaY,
        };
    }

    setCropValue(point, iconPoint) {
        if (!iconPoint) {
            iconPoint = point;
        }
        this.cropContainerRef.el.style.setProperty("--o-crop-x", `${point.x}px`);
        this.cropContainerRef.el.style.setProperty("--o-crop-y", `${point.y}px`);
        this.cropContainerRef.el.style.setProperty("--o-crop-icon-x", `${iconPoint.x}px`);
        this.cropContainerRef.el.style.setProperty("--o-crop-icon-y", `${iconPoint.y}px`);
    }

    pointerDown(event) {
        event.preventDefault();
        if (event.target.matches(".o_crop_icon")) {
            this.computeOverlayPosition();
            this.isMoving = true;
        }
    }

    pointerMove(event) {
        if (!this.isMoving) {
            return;
        }
        let eventPosition;
        if (event.touches && event.touches.length) {
            eventPosition = event.touches[0];
        } else {
            eventPosition = event;
        }
        const { clientX, clientY } = eventPosition;
        const restrictedPosition = this.boundPoint(
            {
                x: clientX,
                y: clientY,
            },
            this.boundaryOverlay
        );
        this.relativePosition = {
            x: restrictedPosition.x - this.boundaryOverlay.left,
            y: restrictedPosition.y - this.boundaryOverlay.top,
        };
        this.calculateAndSetTransparentRect(this.relativePosition);
    }

    pointerUp(event) {
        this.isMoving = false;
        this.executeOnResizeCallback();
    }
}
