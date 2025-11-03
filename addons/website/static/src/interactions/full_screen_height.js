import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { isVisible } from "@web/core/utils/ui";

export class FullScreenHeight extends Interaction {
    static selector = ".o_full_screen_height";
    dynamicContent = {
        _window: {
            "t-on-resize.noUpdate": this.debounced(this.updateContent, 250, {
                leading: true,
                trailing: true,
            }),
        },
        _root: {
            "t-att-style": () => ({
                "min-height": this.isActive
                    ? `${this.computeIdealHeight()}px !important`
                    : undefined,
            }),
        },
    };

    setup() {
        this.inModal = !!this.el.closest(".modal");
        const currentHeight = this.el.getBoundingClientRect().height;
        const idealHeight = this.computeIdealHeight();
        // Only initialize if taller than the ideal height as some extra css
        // rules may alter the full-screen-height class behavior in some
        // cases (blog...).
        this.isActive = !isVisible(this.el) || currentHeight > idealHeight + 1;
    }

    computeIdealHeight() {
        // Compute the smallest viewport height (svh) to use to set up the ideal
        // height of the element, which won't flicker based on the viewport
        // resize in mobile (when its browser UI changes).
        // TODO: should try to use svh directly, combined with `calc` and
        // CSS variables to avoid this JS as much as possible... but see below:
        // can't because of Arc browser).
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        if (
            !this.smallestViewportHeight ||
            // Update svh definition only if the viewport resize seems to
            // not be to a mobile browser UI change (e.g. Arc browser
            // mistakenly changes svh while its UI changes at the moment).
            Math.abs(viewportWidth - this.previousViewportWidth) > 15 ||
            Math.abs(viewportHeight - this.previousViewportHeight) > 150
        ) {
            this.previousViewportWidth = viewportWidth;
            this.previousViewportHeight = viewportHeight;
            const el = document.createElement("div");
            el.classList.add("vh-100");
            el.style.position = "fixed";
            el.style.top = "0";
            el.style.pointerEvents = "none";
            el.style.visibility = "hidden";
            el.style.setProperty("height", "100svh", "important");
            document.body.appendChild(el);
            this.smallestViewportHeight = parseFloat(el.getBoundingClientRect().height);
            document.body.removeChild(el);
        }

        if (this.inModal) {
            return this.smallestViewportHeight;
        }

        // Doing it that way allows to consider fixed headers, hidden headers,
        // connected users, ...
        const firstContentEl = this.el.ownerDocument.querySelector(
            "#wrapwrap > main > :first-child"
        ); // first child to consider the padding-top of main
        const mainTopPos =
            firstContentEl.getBoundingClientRect().top +
            this.el.ownerDocument.documentElement.scrollTop;
        return this.smallestViewportHeight - mainTopPos;
    }
}

registry.category("public.interactions").add("website.full_screen_height", FullScreenHeight);
