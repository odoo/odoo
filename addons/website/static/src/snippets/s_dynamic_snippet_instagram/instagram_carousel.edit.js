import { InstagramCarousel } from "./instagram_carousel";
import { registry } from "@web/core/registry";

const InstagramCarouselEdit = (I) =>
    class extends I {
        setup() {
            super.setup();
            // The carousel keeps the height of its tallest slide: compute it
            // again when the look of the posts changes (e.g. when they become
            // tiles), so that its arrows stay centered on them.
            const getPostClasses = () =>
                [...this.el.classList]
                    .filter((className) => className.startsWith("o_instagram_"))
                    .join(" ");
            let postClasses = getPostClasses();
            const observer = new MutationObserver(() => {
                if (getPostClasses() !== postClasses) {
                    postClasses = getPostClasses();
                    this.el
                        .querySelector(".carousel")
                        ?.dispatchEvent(new CustomEvent("content_changed"));
                }
            });
            observer.observe(this.el, { attributeFilter: ["class"] });
            this.registerCleanup(() => observer.disconnect());
        }
    };

registry.category("public.interactions.edit").add("website.instagram_carousel", {
    Interaction: InstagramCarousel,
    mixin: InstagramCarouselEdit,
});
