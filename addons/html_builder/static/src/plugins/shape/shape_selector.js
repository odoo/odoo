import { Component, useRef } from "@odoo/owl";
import { getShapeURL } from "../image/image_helpers";
import { useBuilderComponents } from "@html_builder/core/utils";

export class ShapeSelector extends Component {
    static template = "html_builder.shapeSelector";
    static props = {
        onClose: Function,
        shapeGroups: Object,
        shapeActionId: String,
        buttonWrapperClassName: { type: String, optional: true },
        imgThroughDiv: { type: Boolean, optional: true },
        getShapeUrl: { type: Function, optional: true },
    };

    setup() {
        useBuilderComponents();
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
