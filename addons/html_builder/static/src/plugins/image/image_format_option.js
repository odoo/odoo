import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getImageSrc, getMimetype } from "@html_editor/utils/image";
import { clamp } from "@web/core/utils/numbers";

export class ImageFormatOption extends BaseOptionComponent {
    static template = "html_builder.ImageFormat";
    static dependencies = ["imageFormatOption"];
    static props = {
        level: { type: Number, optional: true },
        computeMaxDisplayWidth: { type: Function, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
    MAX_SUGGESTED_WIDTH = 1920;
    setup() {
        super.setup();
        const { computeAvailableFormats } = this.dependencies.imageFormatOption;
        this.state = useDomState(async (editingElement) => {
            const formats = await computeAvailableFormats(
                editingElement,
                this.computeMaxDisplayWidth.bind(this)
            );
            const hasSrc = !!getImageSrc(editingElement);
            const mimetype = getMimetype(editingElement);
            const compressionUnsupported =
                mimetype === "image/webp" && this.webpCompressionUnuspported();
            return {
                showQuality: ["image/jpeg", "image/webp"].includes(mimetype),
                compressionUnsupported: compressionUnsupported,
                formats: hasSrc ? formats : [],
            };
        });
    }
    computeMaxDisplayWidth(img) {
        if (this.props.computeMaxDisplayWidth) {
            return this.props.computeMaxDisplayWidth(img);
        }
        return computeMaxDisplayWidth(img, this.MAX_SUGGESTED_WIDTH);
    }
    webpCompressionUnuspported() {
        const canvas = document.createElement("canvas");
        canvas.width = canvas.height = 1;
        return canvas.toDataURL("image/webp").slice(0, 16) !== "data:image/webp;";
    }
}

export function computeMaxDisplayWidth(img, MAX_SUGGESTED_WIDTH = 1920) {
    const window = img.ownerDocument.defaultView;
    if (!window) {
        return;
    }
    const computedStyles = window.getComputedStyle(img);
    const displayWidth = parseFloat(computedStyles.getPropertyValue("width"));
    const gutterWidth = parseFloat(computedStyles.getPropertyValue("--o-grid-gutter-width")) || 30;

    // For the logos we don't want to suggest a width too small.
    if (img.closest("nav")) {
        return Math.round(Math.min(displayWidth * 3, MAX_SUGGESTED_WIDTH));
        // If the image is in a container(-small), it might get bigger on
        // smaller screens. So we suggest the width of the current image unless
        // it is smaller than the size of the container on the md breapoint
        // (which is where our bootstrap columns fallback to full container
        // width since we only use col-lg-* in Odoo).
    } else if (img.closest(".container, .o_container_small")) {
        const mdContainerMaxWidth =
            parseFloat(computedStyles.getPropertyValue("--o-md-container-max-width")) || 720;
        const mdContainerInnerWidth = mdContainerMaxWidth - gutterWidth;
        return Math.round(clamp(displayWidth, mdContainerInnerWidth, MAX_SUGGESTED_WIDTH));
        // If the image is displayed in a container-fluid, it might also get
        // bigger on smaller screens. The same way, we suggest the width of the
        // current image unless it is smaller than the max size of the container
        // on the md breakpoint (which is the LG breakpoint since the container
        // fluid is full-width).
    } else if (img.closest(".container-fluid")) {
        const lgBp = parseFloat(computedStyles.getPropertyValue("--breakpoint-lg")) || 992;
        const mdContainerFluidMaxInnerWidth = lgBp - gutterWidth;
        return Math.round(clamp(displayWidth, mdContainerFluidMaxInnerWidth, MAX_SUGGESTED_WIDTH));
    }
    // If it's not in a container, it's probably not going to change size
    // depending on breakpoints. We still keep a margin safety.
    return Math.round(Math.min(displayWidth * 1.5, MAX_SUGGESTED_WIDTH));
}
