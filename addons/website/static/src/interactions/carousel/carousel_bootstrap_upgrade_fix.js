import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

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
            "t-on-slide.bs.carousel": () => this.sliding = true,
            "t-on-slid.bs.carousel": () => this.sliding = false,
            "t-att-class": () => ({
                "o_carousel_sliding": this.sliding,
            }),
        },
    };
    OLD_AUTO_SLIDING_SNIPPETS = ["s_image_gallery"];
    carouselOptions = undefined;

    setup() {
        this.sliding = false;
        this.hasInterval = ![undefined, "false", "0"].includes(this.el.dataset.bsInterval);
        if (!this.hasInterval && this.el.dataset.bsRide) {
            // A bsInterval of 0 (or false or undefined) is intended to not
            // auto-slide. With current Bootstrap version, a value of 0 will
            // mean auto-slide without any delay (very fast). To prevent this,
            // we remove the bsRide.
            delete this.el.dataset.bsRide;
        } else if (this.hasInterval && !this.el.dataset.bsRide) {
            // Re-add bsRide on carousels that don't have it but still have
            // a bsInterval. E.g. s_image_gallery must auto-slide on load,
            // while others only auto-slide on mouseleave.
            //
            // In the case of s_image_gallery that has a bsRide = "true"
            // instead of "carousel", it's better not to change the behavior and
            // let the user update the snippet manually to avoid making changes
            // that they don't expect.
            const snippetName = this.el.closest("[data-snippet]")?.dataset.snippet;
            this.el.dataset.bsRide = this.OLD_AUTO_SLIDING_SNIPPETS.includes(snippetName) ? "carousel" : "true";
        }
    }

    async willStart() {
        if (this.hasInterval || this.el.dataset.bsRide) {
            // Wait for carousel to finish sliding.
            if (this.el.classList.contains("o_carousel_sliding")) {
                await new Promise(resolve => {
                    this.el.addEventListener("slid.bs.carousel", () => resolve(), { once: true });
                });
            }
            window.Carousel.getInstance(this.el)?.dispose();
        }
    }

    start() {
        if (this.hasInterval || this.el.dataset.bsRide) {
            // Respawn carousel.
            const carousel = window.Carousel.getOrCreateInstance(this.el, this.carouselOptions);
            this.registerCleanup(() => carousel.dispose());
        }
    }
}

registry
    .category("public.interactions")
    .add("website.carousel_bootstrap_upgrade_fix", CarouselBootstrapUpgradeFix);
