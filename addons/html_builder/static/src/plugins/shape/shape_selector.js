import { BaseOptionComponent } from "@html_builder/core/utils";
import { useRef } from "@odoo/owl";
import { getShapeURL } from "../image/image_helpers";

export class ShapeSelector extends BaseOptionComponent {
    static template = "html_builder.shapeSelector";
    static props = {
        onClose: Function,
        shapeGroups: Object,
        shapeActionId: String,
        buttonWrapperClassName: { type: String, optional: true },
        imgThroughDiv: { type: Boolean, optional: true },
        getShapeUrl: { type: Function, optional: true },
        shapeData: Object,
    };

    setup() {
        super.setup();
        this.rootRef = useRef("root");
    }
    getShapeUrl(shapePath) {
        if (this.props.getShapeUrl) {
            const baseUrl = this.props.getShapeUrl(shapePath);
            if (baseUrl) {
                const { colors, flip: flipProxy } = this.props.shapeData;
                const flip = Array.from(flipProxy);
                const urlMatch = baseUrl.match(/url\(["']?(.*?)["']?\)/);
                const url = new URL(urlMatch[1], window.location.origin);

                if (!Object.keys(colors).length == 0) {
                    Object.entries(colors).forEach(([key, value]) => {
                        url.searchParams.set(key, value);
                    });
                    if (flip.includes("y")) {
                        url.searchParams.set("flip", "y");
                    }
                }
                return `url("${url.toString()}")`;
            } else {
                return getShapeURL(shapePath);
            }
        } else {
            return getShapeURL(shapePath);
        }
    }
    scrollToShapes(id) {
        this.rootRef.el
            ?.querySelector(`[data-shape-group-id="${id}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}
