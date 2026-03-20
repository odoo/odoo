import { Decor } from "./decor";
import {
    applyDefaults,
    removeNullishAndDefault,
    STATIC_IMG_BASE_URL,
} from "@pos_restaurant/app/services/floor_plan/utils/utils";

const defaults = {
    allowText: false,
    allowBorder: false,
    allowBackground: false,
};

export class Image extends Decor {
    constructor(data) {
        super(applyDefaults(data, defaults));
        this.allowBackground = false;
        this.allowBorder = false;
        this.allowText = false;
        this.shape = "image";
        if (!this.url) {
            this.url = this.name ? STATIC_IMG_BASE_URL + "/" + this.name : "/web/image/" + this.id;
        }
    }

    getCssStyle() {
        let style = super.getCssStyle();
        if (this.url) {
            style += `background-image: url('${this.url}');`;
            style += `background-size: cover;`;
            style += `background-position: center;`;
            style += `background-repeat: no-repeat;`;
        }
        return style;
    }

    isSideResizeAllowed() {
        return false;
    }
    isCornerResizeAllowed() {
        return true;
    }

    isResizeMaintainRatio() {
        return true;
    }

    get isImage() {
        return true;
    }

    get raw() {
        const data = {
            ...super.raw,
            url: this.url,
            name: this.name,
            id: this.id,
        };
        return removeNullishAndDefault(data, defaults);
    }
}
