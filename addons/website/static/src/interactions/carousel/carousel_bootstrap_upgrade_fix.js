import { usePlugin } from "@odoo/owl";
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

/**
 * This class is used to fix carousel auto-slide behavior in Odoo 17.4 and up.
 * It handles upgrade cases from lower versions.
 * TODO find a way to get rid of this with an upgrade script?
 */
export class CarouselBootstrapUpgradeFix extends Interaction {
    // Only consider our known carousel snippets. A bootstrap carousel could
    // have been added in an embed code snippet, or in any custom snippet. In
    // that case, we consider that it should use the new default BS behavior,
    // assuming the user / the developer of the custo should have updated the
    // behavior as wanted themselves.
    // Note: dynamic snippets are handled separately (TODO review).
    static selector = [
        "[data-snippet='s_image_gallery'] .carousel",
        "[data-snippet='s_carousel'] .carousel",
        "[data-snippet='s_quotes_carousel'] .carousel",
        "[data-snippet='s_quotes_carousel_minimal'] .carousel",
        "[data-snippet='s_carousel_intro'] .carousel",
        "#o-carousel-product.carousel",
    ].join(", ");
    dynamicContent = {
        _root: {
            "t-on-slide.bs.carousel": () => (this.sliding = true),
            "t-on-slid.bs.carousel": () => (this.sliding = false),
            "t-att-class": () => ({
                o_carousel_sliding: this.sliding,
            }),
        },
    };
    carouselOptions = undefined;

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
        this.sliding = false;
        this.hasInterval = ![undefined, "false", "0"].includes(this.el.dataset.bsInterval);
    }

    async willStart() {
        if (this.hasInterval || this.el.dataset.bsRide) {
            // Wait for carousel to finish sliding.
            if (this.el.classList.contains("o_carousel_sliding")) {
                await new Promise((resolve) => {
                    this.addListener(this.el, "slid.bs.carousel", () => resolve(), { once: true });
                });
            }
            // { force: true }: this respawn needs a genuinely fresh
            // instance right now, not "whenever every other owner (e.g.
            // CarouselSlider) has released its own reference" - otherwise
            // the `getOrCreateInstance` below could silently hand back the
            // still-alive old one. Safe here because no owner of this
            // carousel caches a persistent reference to the instance
            // (CarouselSlider re-fetches fresh from `this.bootstrap` before
            // every use, for this very reason), so none can be left stale.
            this.bootstrap.disposeBootstrapInstance(window.Carousel.getInstance(this.el), {
                force: true,
            });
        }
    }

    start() {
        if (this.hasInterval || this.el.dataset.bsRide) {
            // Respawn carousel.
            this.bootstrap.getOrCreateInstance(window.Carousel, this.el, this.carouselOptions);
        }
    }
}

registry
    .category("public.interactions")
    .add("website.carousel_bootstrap_upgrade_fix", CarouselBootstrapUpgradeFix);
