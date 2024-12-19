import { Component, useExternalListener, useState } from "@odoo/owl";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { registry } from "@web/core/registry";
import { ImageTransformation } from "./image_transformation";

export class ImageTransformButton extends Component {
    static template = "html_editor.ImageTransformButton";
    static props = {
        icon: String,
        getSelectedImage: Function,
        resetImageTransformation: Function,
        addStep: Function,
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        ...toolbarButtonProps,
        activeTitle: String,
    };

    setup() {
        this.state = useState({ active: false });
        this.mouseDownInsideTransform = false;
        // We close the image transform when we click outside any element not related to it
        // When the mousedown of the click is inside the image transform and mouseup is outside
        // while resizing or rotating the image it will consider the click as being done outside
        // image transform. So we need to keep track if the mousedown is inside or outside to
        // know if we want to close the image transform component or not.
        useExternalListener(this.props.document, "mousedown", (ev) => {
            if (this.isNodeInsideTransform(ev.target)) {
                this.mouseDownInsisdeTransform = true;
            } else {
                this.closeImageTransformation();
                this.mouseDownInsideTransform = false;
            }
        });
        useExternalListener(this.props.document, "click", (ev) => {
            if (!this.isNodeInsideTransform(ev.target) && !this.mouseDownInsideTransform) {
                this.closeImageTransformation();
            }
            this.mouseDownInsideTransform = false;
        });
        // When we click on any character the image is deleted and we need to close the image transform
        // We handle this by selectionchange
        useExternalListener(this.props.document, "selectionchange", (ev) => {
            this.closeImageTransformation();
        });
    }

    isNodeInsideTransform(node) {
        if (!node) {
            return false;
        }
        if (node.nodeType === Node.TEXT_NODE) {
            node = node.parentElement;
        }
        if (node.matches('[name="image_transform"], [name="image_transform"] *')) {
            return true;
        }
        if (
            this.isImageTransformationOpen() &&
            node.matches(
                ".transfo-container, .transfo-container div, .transfo-container i, .transfo-container span"
            )
        ) {
            return true;
        }
        return false;
    }

    onButtonClick() {
        this.handleImageTransformation(this.props.getSelectedImage());
    }

    handleImageTransformation(image) {
        if (this.isImageTransformationOpen()) {
            this.props.resetImageTransformation(image);
            this.closeImageTransformation();
        } else {
            this.openImageTransformation(image);
        }
    }

    openImageTransformation(image) {
        this.state.active = true;
        registry.category("main_components").add("ImageTransformation", {
            Component: ImageTransformation,
            props: {
                image,
                document: this.props.document,
                editable: this.props.editable,
                destroy: () => this.closeImageTransformation(),
                onChange: () => this.props.addStep(),
            },
        });
    }

    isImageTransformationOpen() {
        return registry.category("main_components").contains("ImageTransformation");
    }

    closeImageTransformation() {
        this.state.active = false;
        if (this.isImageTransformationOpen()) {
            registry.category("main_components").remove("ImageTransformation");
        }
    }
}
