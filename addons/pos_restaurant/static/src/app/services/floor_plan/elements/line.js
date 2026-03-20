import { getColorRGBA } from "@pos_restaurant/app/services/floor_plan/utils/colors";
import { Decor } from "./decor";
import {
    applyDefaults,
    removeNullishAndDefault,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";

const defaults = {
    rounded: false,
    allowText: false,
    allowBorder: false,
    allowBackground: false,
    borderStyle: "solid",
    color: "black",
};

export class Line extends Decor {
    constructor(data) {
        super(applyDefaults(data, defaults));
        this.height = data.thickness || data.height || 20;
        this.width = data.width || 200;
        this.allowText = false;
        this.allowBorder = false;
        this.allowBackground = false;
        this.shape = "line";
    }

    getCssStyle() {
        let style = super.getCssStyle();

        if (this.type === "double") {
            style += `border-top: ${this.height / 3}px ${
                this.borderStyle || "solid"
            } ${getColorRGBA(this.borderColor)};border-bottom: ${this.height / 3}px ${
                this.borderStyle || "solid"
            } ${getColorRGBA(this.borderColor)};`;

            return style;
        }

        if (this.borderStyle === "solid") {
            style += `background-color:${getColorRGBA(this.borderColor)};`;
            if (this.rounded) {
                style += `border-radius:${this.height / 2}px;`;
            }
        } else {
            style += `border-top: ${this.height}px ${this.borderStyle || "solid"} ${getColorRGBA(
                this.borderColor
            )};`;
        }

        return style;
    }

    set thickness(value) {
        this.height = value;
    }

    get thickness() {
        return this.height;
    }

    get style() {
        return this.borderStyle;
    }

    set style(value) {
        this.borderStyle = value;
    }

    set color(value) {
        this.borderColor = value;
    }

    get color() {
        return this.borderColor;
    }

    isLineEndResizeAllowed() {
        return true;
    }

    isCornerResizeAllowed() {
        return false;
    }

    isSideResizeAllowed() {
        return false;
    }

    isResizeMaintainRatio() {
        return true;
    }

    get isLine() {
        return true;
    }

    get raw() {
        return removeNullishAndDefault(
            {
                ...super.raw,
                type: this.type,
                rounded: this.rounded,
                style: this.style,
                color: this.color,
            },
            defaults
        );
    }
}
