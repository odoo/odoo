import { Interaction } from "@web/public/interaction";

import { SIZES, utils as uiUtils } from "@web/core/ui/ui_service";
import { compensateScrollbar } from "@web/core/utils/scrolling";

export class BaseHeader extends Interaction {
    dynamicContent = {
        _document: {
            "t-on-scroll": this.onScroll,
        },
        _window: {
            "t-on-resize": this.onResize,
        },
        _body: {
            "t-att-class": () => ({
                "overflow-hidden": this.bodyNoScroll,
            }),
        },
        _root: {
            "t-on-transitionend": () => this.adaptToHeaderChangeLoop(-1),
            "t-att-class": () => ({
                "o_top_fixed_element": this.isVisible,
                "o_header_affixed": this.cssAffixed,
                "o_header_is_scrolled": this.isScrolled,
                "o_header_no_transition": !this.transitionActive,
            }),
        },
        ".offcanvas": {
            "t-on-show.bs.offcanvas": this.disableScroll,
            "t-on-hide.bs.offcanvas": this.enableScroll,
        },
        // Compatibility: can probably be removed, there is no such elements in
        // default navbars... although it could be used by custo.
        ".navbar-collapse": {
            "t-on-show.bs.collapse": this.disableScroll,
            "t-on-hide.bs.collapse": this.enableScroll,
        },
    };

    //--------------------------------------------------------------
    // Life Cycle
    //--------------------------------------------------------------

    setup() {
        this.topGap = 0;
        this.atTop = false;

        this.cssAffixed = false;
        this.bodyNoScroll = false;

        this.transitionCount = 0;
        this.transitionActive = true;

        this.isVisible = true;
        this.isScrolled = false;
        this.forcedScroll = 0;

        this.isOverlay = !!this.el.closest(".o_header_overlay, .o_header_overlay_theme");

        this.mainEl = this.el.parentElement.querySelector("main");
        this.hideEl = this.el.querySelector(".o_header_hide_on_scroll");
        this.hideElHeight = this.hideEl?.getBoundingClientRect().height;

        this.scrollingElement = document.scrollingElement;
        const navbarEl = this.el.querySelector(".navbar");
        const navBreakpoint = navbarEl ? Object.keys(SIZES).find((size) =>
            navbarEl.classList.contains(`navbar-expand-${size.toLowerCase()}`)
        ) : "LG";
        this.breakpointSize = SIZES[navBreakpoint];    }

    start() {
        this.services.website_menus.triggerCallbacks();
        if (this.scrollingElement.scrollTop > 0) {
            this.adjustPosition();
        }
    }

    isSmall() {
        return uiUtils.getSize() < this.breakpointSize;
    }
    
    //--------------------------------------------------------------
    // Event Handlers
    //--------------------------------------------------------------

    disableScroll() {
        if (this.isSmall()) {
            this.bodyNoScroll = true;
        }
    }

    enableScroll() {
        this.bodyNoScroll = false;
    }

    onResize() {
        this.adjustScrollbar();
        if (
            document.body.classList.contains('overflow-hidden')
            && !this.isSmall()
        ) {
            const offCanvasEls = this.el.querySelectorAll(".offcanvas.show");
            for (const offCanvasEl of offCanvasEls) {
                Offcanvas.getOrCreateInstance(offCanvasEl).hide();
            }
            // Compatibility: can probably be removed, there is no such elements in
            // default navbars... although it could be used by custo.
            const collapseEls = this.el.querySelectorAll(".navbar-collapse.show");
            for (const collapseEl of collapseEls) {
                Collapse.getOrCreateInstance(collapseEl).hide();
            }
        }
        else {
            this.adjustMainPadding();
        }
    }

    //--------------------------------------------------------------
    // Animation Handlers
    //--------------------------------------------------------------

    adaptToHeaderChange() {
        this.services.website_menus.triggerCallbacks();
        this.adjustMainPadding();
    }

    adaptToHeaderChangeLoop(addCount = 0) {
        this.adaptToHeaderChange();
        this.transitionCount = Math.max(0, this.transitionCount + addCount);

        // As long as we detected a transition start without its related
        // transition end, keep updating the main padding top.
        if (this.transitionCount > 0) {
            this.el.classList.add("o_transitioning");
            this.waitForAnimationFrame(() => this.adaptToHeaderChangeLoop());

            // The normal case would be to have the transitionend event to be
            // fired but we cannot rely on it, so we use a timeout as fallback.
            if (addCount !== 0) {
                clearTimeout(this.changeLoopTimer);
                this.changeLoopTimer = this.waitForTimeout(() => this.adaptToHeaderChangeLoop(- this.transitionCount), 500);
            }
        } else {
            // When we detected all transitionend events, we need to stop the
            // setTimeout fallback.
            this.el.classList.remove("o_transitioning");
            clearTimeout(this.changeLoopTimer);
        }
    }

    //--------------------------------------------------------------
    // Animation Trigger
    //--------------------------------------------------------------

    transformShow() {
        this.isVisible = true;
        this.el.style.transform = this.atTop ? "" : `translate(0, -${this.forcedScroll + this.topGap}px)`;
        this.adaptToHeaderChangeLoop(1);
    }

    transformHide() {
        this.isVisible = false;
        this.el.style.transform = "translate(0, -100%)";
        this.adaptToHeaderChangeLoop(1);
    }

    //--------------------------------------------------------------
    // Change Handlers
    //--------------------------------------------------------------

    adjustPosition() {
        // When the url contains #aRandomSection, prevent the navbar to overlap
        // on the section, for this, we scroll as many px as the navbar height.
        this.scrollingElement.scrollBy(0, - this.el.offsetHeight);
    }

    adjustScrollbar() {
        compensateScrollbar(this.el, this.cssAffixed, false, 'right');
    }

    adjustMainPadding() {
        if (this.isOverlay) {
            return;
        }
        this.mainEl.style.setProperty("padding-top", this.cssAffixed ? this.getHeaderHeight() + "px" : "");
    }

    //--------------------------------------------------------------
    // Utils
    //--------------------------------------------------------------

    getHeaderHeight() {
        if (this.isSmall()) {
            // Ensure we don't consider the hiddenOnScroll element on mobile
            return this.el.getBoundingClientRect().height;
        }
        if (this.hideEl?.classList.contains("hidden")) {
            // Ensure the header height stays the same on desktop
            return this.hideElHeight + this.el.getBoundingClientRect().height;
        }
        this.hideElHeight = this.hideEl?.getBoundingClientRect().height || this.hideElHeight;
        return this.el.getBoundingClientRect().height;
    }

    toggleCSSAffixed(useAffixed) {
        this.cssAffixed = useAffixed;
        this.adaptToHeaderChange();
        this.adjustScrollbar();
    }
}
