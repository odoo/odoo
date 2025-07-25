import { Component, useExternalListener, useState } from "@odoo/owl";
import { toolbarButtonProps } from "@html_editor/main/toolbar/toolbar";
import { registry } from "@web/core/registry";
import { ImageTransformation } from "./image_transformation";

export function useImageTransform({ document, closeImageTransformation, buttonSelector }) {
    let pointerDownInsideTransform = false;

    // We close the image transform when we click outside any element not
    // related to it. When the pointerdown of the click is inside the image
    // transform and pointerup is outside while resizing or rotating the
    // image it will consider the click as being done outside image transform.
    // So we need to keep track if the pointerdown is inside or outside to know
    // if we want to close the image transform component or not.
    useExternalListener(document, "pointerdown", (ev) => {
        if (isNodeInsideTransform(ev.target)) {
            pointerDownInsideTransform = true;
        } else {
            closeImageTransformation();
            pointerDownInsideTransform = false;
        }
    });
    useExternalListener(
        document,
        "click",
        (ev) => {
            if (!isNodeInsideTransform(ev.target) && !pointerDownInsideTransform) {
                closeImageTransformation();
            }
            pointerDownInsideTransform = false;
        },
        { capture: true }
    );
    // When we click on any character the image is deleted and we need to close
    // the image transform. We handle this by selectionchange.
    useExternalListener(document, "selectionchange", (ev) => {
        closeImageTransformation();
    });

    function isNodeInsideTransform(node) {
        if (!node) {
            return false;
        }
        if (node.nodeType === Node.TEXT_NODE) {
            node = node.parentElement;
        }
        if (node.matches(buttonSelector)) {
            return true;
        }
        if (isImageTransformationOpen() && node.matches(".transfo-controls, .transfo-controls *")) {
            return true;
        }
        return false;
    }

    function isImageTransformationOpen() {
        return registry.category("main_components").contains("ImageTransformation");
    }

    return { isImageTransformationOpen };
}

export class ImageTransformButton extends Component {
    static template = "html_editor.ImageTransformButton";
    static props = {
        id: String,
        icon: String,
        title: String,
        getTargetedImage: Function,
        resetImageTransformation: Function,
        addStep: Function,
        document: { validate: (p) => p.nodeType === Node.DOCUMENT_NODE },
        editable: { validate: (p) => p.nodeType === Node.ELEMENT_NODE },
        ...toolbarButtonProps,
        activeTitle: String,
    };

    setup() {
        this.state = useState({ active: false });
        this.transform = useImageTransform({
            document: this.props.document,
            closeImageTransformation: this.closeImageTransformation.bind(this),
            buttonSelector: '[name="image_transform"], [name="image_transform"] *',
        });
    }

    onButtonClick() {
        this.handleImageTransformation(this.props.getTargetedImage());
    }

    handleImageTransformation(image) {
        if (this.transform.isImageTransformationOpen()) {
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

    closeImageTransformation() {
        this.state.active = false;
        if (this.transform.isImageTransformationOpen()) {
            registry.category("main_components").remove("ImageTransformation");
        }
    }
}
