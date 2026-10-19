import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillDestroy, useListener } from "@odoo/owl";
import { registry } from "@web/core/registry";

/**
 * Closes the ImageTransformation component when the user clicks or changes
 * selection outside its boundaries.
 *
 * @param {Object} params
 * @param {Document} params.document - The document to attach listeners to.
 *   May be an iframe's contentDocument rather than top-level window.document.
 * @param {function(): void} params.closeImageTransformation - Callback to
 *   close and unmount the ImageTransformation component.
 * @param {string} params.buttonSelector - CSS selector matching the toolbar
 *   button(s) that open the component; clicks on these won't trigger a close.
 * @returns {{isImageTransformationOpen: function(): boolean}} Object containing
 *   the isImageTransformationOpen method which returns true when
 *   ImageTransformation is registered in main_components.
 */
function useImageTransform({ document, closeImageTransformation, buttonSelector }) {
    let pointerDownInsideTransform = false;

    // We close the image transform when we click outside any element not
    // related to it. When the pointerdown of the click is inside the image
    // transform and pointerup is outside while resizing or rotating the
    // image it will consider the click as being done outside image transform.
    // So we need to keep track if the pointerdown is inside or outside to know
    // if we want to close the image transform component or not.
    useListener(document, "pointerdown", (ev) => {
        if (isNodeInsideTransform(ev.target)) {
            pointerDownInsideTransform = true;
        } else {
            closeImageTransformation();
            pointerDownInsideTransform = false;
        }
    });
    useListener(
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
    useListener(document, "selectionchange", (ev) => {
        closeImageTransformation();
    });

    function isNodeInsideTransform(node) {
        if (!node) {
            return false;
        }
        if (node.nodeType === Node.TEXT_NODE) {
            node = node.parentElement;
        }
        return (
            node.matches(buttonSelector) ||
            (isImageTransformationOpen() && node.matches(".transfo-controls, .transfo-controls *"))
        );
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
