import { BaseOptionComponent } from "@html_builder/core/utils";
import { onWillDestroy, useExternalListener } from "@odoo/owl";
import { registry } from "@web/core/registry";

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

export class ImageTransformOption extends BaseOptionComponent {
    static template = "website.ImageTransformOption";

    setup() {
        super.setup();
        this.transform = useImageTransform({
            document: document,
            closeImageTransformation: this.closeImageTransformation.bind(this),
            buttonSelector:
                '[data-action-id="transformImage"], [data-action-id="transformImage"] *',
        });
        onWillDestroy(() => {
            this.closeImageTransformation();
        });
    }

    closeImageTransformation() {
        if (this.transform.isImageTransformationOpen()) {
            registry.category("main_components").remove("ImageTransformation");
        }
    }
}
