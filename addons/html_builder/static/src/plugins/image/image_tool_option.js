import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { ImageShapeOption } from "./image_shape_option";
import { clamp } from "@web/core/utils/numbers";
import { KeepLast } from "@web/core/utils/concurrency";
import { getMimetype } from "@html_editor/utils/image";

export class ImageToolOption extends BaseOptionComponent {
    static template = "html_builder.ImageToolOption";
    static components = {
        ImageShapeOption,
    };
    static props = {};
    MAX_SUGGESTED_WIDTH = 1920;
    setup() {
        super.setup();
        const keepLast = new KeepLast();
        this.state = useDomState((editingElement) => {
            keepLast
                .add(
                    this.env.editor.shared.imageOptimize.computeAvailableFormats(
                        editingElement,
                        this.computeMaxDisplayWidth.bind(this)
                    )
                )
                .then((formats) => {
                    this.state.formats = formats;
                });
            return {
                isCustomFilter: editingElement.dataset.glFilter === "custom",
                showQuality: ["image/jpeg", "image/webp"].includes(getMimetype(editingElement)),
                formats: [],
            };
        });
    }
    computeMaxDisplayWidth(img) {
        const computedStyles = window.getComputedStyle(img);
        const displayWidth = parseFloat(computedStyles.getPropertyValue("width"));
        const gutterWidth =
            parseFloat(computedStyles.getPropertyValue("--o-grid-gutter-width")) || 30;

        // For the logos we don't want to suggest a width too small.
        if (img.closest("nav")) {
            return Math.round(Math.min(displayWidth * 3, this.MAX_SUGGESTED_WIDTH));
            // If the image is in a container(-small), it might get bigger on
            // smaller screens. So we suggest the width of the current image unless
            // it is smaller than the size of the container on the md breapoint
            // (which is where our bootstrap columns fallback to full container
            // width since we only use col-lg-* in Odoo).
        } else if (img.closest(".container, .o_container_small")) {
            const mdContainerMaxWidth =
                parseFloat(computedStyles.getPropertyValue("--o-md-container-max-width")) || 720;
            const mdContainerInnerWidth = mdContainerMaxWidth - gutterWidth;
            return Math.round(clamp(displayWidth, mdContainerInnerWidth, this.MAX_SUGGESTED_WIDTH));
            // If the image is displayed in a container-fluid, it might also get
            // bigger on smaller screens. The same way, we suggest the width of the
            // current image unless it is smaller than the max size of the container
            // on the md breakpoint (which is the LG breakpoint since the container
            // fluid is full-width).
        } else if (img.closest(".container-fluid")) {
            const lgBp = parseFloat(computedStyles.getPropertyValue("--breakpoint-lg")) || 992;
            const mdContainerFluidMaxInnerWidth = lgBp - gutterWidth;
            return Math.round(
                clamp(displayWidth, mdContainerFluidMaxInnerWidth, this.MAX_SUGGESTED_WIDTH)
            );
        }
        // If it's not in a container, it's probably not going to change size
        // depending on breakpoints. We still keep a margin safety.
        return Math.round(Math.min(displayWidth * 1.5, this.MAX_SUGGESTED_WIDTH));
    }
}
