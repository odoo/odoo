import { Decor } from "./decor.js";
import {
    applyDefaults,
    removeNullishAndDefault,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";

const defaults = {
    allowBackground: false,
    allowBorder: true,
    allowText: false,
};

export class OnlyBorderDecor extends Decor {
    constructor(data) {
        super(applyDefaults(data, defaults));
        this.shape = "rect";
        this.onlyBorder = true;
        this.allowBackground = false;
        this.allowBorder = true;
        this.allowText = false;
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

    set thickness(value) {
        this.borderWidth = value;
    }

    get thickness() {
        return this.borderWidth;
    }

    get isOnlyBorder() {
        return this.onlyBorder;
    }
    get hasTransparentArea() {
        return true;
    }

    isResizeMaintainRatio() {
        return false;
    }

    get raw() {
        return removeNullishAndDefault(
            {
                ...super.raw,
                onlyBorder: true,
            },
            defaults
        );
    }
}
