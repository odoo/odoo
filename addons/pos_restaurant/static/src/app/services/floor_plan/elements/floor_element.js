import { calculateBoundsFromTransform } from "@pos_restaurant/app/services/floor_plan/utils/bounds_calculator";
import {
    applyDefaults,
    removeNullishAndDefault,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";

export const SHAPE_TYPES = {
    RECTANGLE: "rect",
    CIRCLE: "circle",
    SQUARE: "square",
    OVAL: "oval",
    IMAGE: "image",
    TEXT: "text",
};

const defaults = {
    rotation: 0,
    scale: 1,
};

export class FloorElement {
    constructor(data) {
        data = applyDefaults(data, defaults);
        Object.assign(this, data);
        this.cachedBounds = null;
        if (!data.width && !data.height) {
            const defaultSize = this.getDefaultSize(this.shape);
            if (defaultSize) {
                this.width = defaultSize.width;
                this.height = defaultSize.height;
            }
        }
    }

    set left(value) {
        this._left = Math.round(value);
        this.clearBoundsCache();
    }

    get left() {
        return this._left || 0;
    }

    set top(value) {
        this._top = Math.round(value);
        this.clearBoundsCache();
    }

    get top() {
        return this._top || 0;
    }

    set width(value) {
        this._width = Math.round(value);
        this.clearBoundsCache();
    }

    get width() {
        return this._width;
    }

    set height(value) {
        this._height = Math.round(value);
        this.clearBoundsCache();
    }

    get height() {
        return this._height;
    }

    set rotation(value) {
        this._rotation = value || 0; // Keep rotation precise
        this.clearBoundsCache();
    }

    get rotation() {
        return this._rotation;
    }

    set scale(value) {
        this._scale = value || 1; // Keep scale precise
        this.clearBoundsCache();
    }

    get scale() {
        return this._scale;
    }

    getDefaultSize(shape) {
        switch (shape) {
            case SHAPE_TYPES.CIRCLE:
            case SHAPE_TYPES.SQUARE:
                return { width: 130, height: 130 };
            case SHAPE_TYPES.OVAL:
            case SHAPE_TYPES.RECTANGLE:
                return { width: 220, height: 110 };
        }
    }

    isEditable() {
        return true;
    }

    get raw() {
        return removeNullishAndDefault(
            {
                uuid: this.uuid,
                left: this.left,
                top: this.top,
                width: this.width,
                height: this.height,
                rotation: this.rotation,
                scale: this.scale,
                shape: this.shape,
            },
            defaults
        );
    }

    getCssStyle(translateX = this.left, translateY = this.top) {
        const transform =
            `translate(${translateX || 0}px,${translateY || 0}px)` +
            (this.rotation && this.rotation !== 0 ? ` rotate(${this.rotation}deg)` : "") +
            (this.scale && this.scale !== 1 ? ` scale(${this.scale})` : "");

        return `width:${this.width ?? 0}px;height:${this.height ?? 0}px;transform:${transform};`;
    }

    isCornerResizeAllowed() {
        return true;
    }

    isSideResizeAllowed() {
        return true; //this.shape === SHAPE_TYPES.RECTANGLE || this.shape === SHAPE_TYPES.OVAL;
    }

    isVerticalResizeAllowed() {
        return true;
    }

    isResizeMaintainRatio() {
        return true;
    }

    getGeometry() {
        return {
            width: this.width,
            height: this.height,
            top: this.top,
            left: this.left,
            scale: this.scale,
            rotation: this.rotation,
            isLine: this.isLine || false, //required for calculateBoundsFromTransform
        };
    }

    getBounds() {
        if (!this.cachedBounds) {
            this.cachedBounds = calculateBoundsFromTransform(this);
        }
        return this.cachedBounds;
    }

    onEdit(editing) {
        this.editing = editing;
    }

    setFloor(floor) {
        this.floor = floor;
    }

    getFloor() {
        return this.floor;
    }

    clearBoundsCache() {
        this.cachedBounds = null;
        this.floor?.clearSizeCache();
    }
}
