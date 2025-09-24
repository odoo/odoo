import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

/**
 * @todo while this solution mitigates the issue, it is not fixing it entirely
 * but mainly, we should find a better solution than a JS solution as soon as
 * one is available and ideally without having to make ugly patches to the SVGs.
 *
 * Due to a bug on Chrome when using browser zoom, there is sometimes a gap
 * between sections with shapes. This gap is due to a rounding issue when
 * positioning the SVG background images. This code reduces the rounding error
 * by ensuring that shape elements always have a width value as close to an
 * integer as possible.
 *
 * Note: a gap also appears between some shapes without zoom. This is likely
 * due to error in the shapes themselves. Many things were done to try and fix
 * this, but the remaining errors will likely be fixed with a review of the
 * shapes in future Odoo versions.
 *
 * /!\
 * If a better solution for stable comes up, this widget behavior may be
 * disabled, avoid depending on it if possible.
 * /!\
 */
export class ZoomedBackgroundShape extends Interaction {
    static selector = ".o_we_shape";
    dynamicContent = {
        _window: {
            "t-on-resize": this.throttled(this.resizeBackgroundShape),
        },
        _root: {
            "t-att-style": () => ({
                left: this.offset,
                right: this.offset,
            }),
        },
    };

    setup() {
        this.offset = undefined;
    }

    start() {
        // This cannot be move in the setup because updateContent
        // is not available yet (interaction not ready)
        this.resizeBackgroundShape();
        this.updateContent();
    }

    resizeBackgroundShape() {
        this.offset = undefined;
        this.updateContent();
        // Get the decimal part of the shape element width.
        let decimalPart = this.el.getBoundingClientRect().width % 1;
        // Round to two decimal places.
        decimalPart = parseFloat(decimalPart.toFixed(2));
        // If the decimal part was 0.99, it was rounded to 1
        // In that case we consider there was no decimal part
        decimalPart = decimalPart == 1 ? 0 : decimalPart;
        // If there is a decimal part. (e.g. Chrome + browser zoom enabled)
        if (decimalPart > 0) {
            // Compensate for the gap by giving an integer width value to the
            // shape by changing its "right" and "left" positions.
            this.offset = `${(decimalPart < 0.5 ? decimalPart : decimalPart - 1) / 2}px`;
            // This never causes the horizontal scrollbar to appear because it
            // only appears if the overflow to the right exceeds 0.333px.
        }
    }
}

registry
    .category("public.interactions")
    .add("website.zoomed_background_shape", ZoomedBackgroundShape);
