import { defaultBuilderComponents } from "@html_builder/core/default_builder_components";
import { Component, useRef } from "@odoo/owl";
import { getShapeURL } from "../image/image_helpers";

export class ShapeSelector extends Component {
    static template = "html_builder.shapeSelector";
    static components = {
        ...defaultBuilderComponents,
    };
    static props = {
        onClose: Function,
        shapeGroups: Object,
        shapeActionId: String,
        buttonWrapperClassName: { type: String, optional: true },
        imgThroughDiv: { type: Boolean, optional: true },
        getShapeUrl: { type: Function, optional: true },
    };

    setup() {
        this.rootRef = useRef("root");
    }
    getShapeUrl(shapePath) {
        return this.props.getShapeUrl ? this.props.getShapeUrl(shapePath) : getShapeURL(shapePath);
    }
    scrollToShapes(id) {
        this.rootRef.el
            ?.querySelector(`[data-shape-group-id="${id}"]`)
            ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}
