import { BaseHeader } from "@website/interactions/header/base_header";
import { registry } from "@web/core/registry";

export class BaseHeaderSpecial extends BaseHeader {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _searchbar: () => this.searchbarEl,
    };
    dynamicContent = {
        ...this.dynamicContent,
        ".o_header_hide_on_scroll .dropdown-toggle": {
            "t-on-show.bs.dropdown": this.onDropdownShow,
        },
        _searchbar: {
            "t-on-input": this.onSearchbarInput,
        },
    };

    setup() {
        super.setup();
        this.isAnimated = false;

        this.position = 0;
        this.checkpoint = 0;
        this.scrollOffset = 200;
        this.scrollingDownward = true;

        this.searchbarEl = this.hideEl?.querySelector(":not(.modal-content) > .o_searchbar_form");
        this.dropdownClickedEl = null;
    }

    /**
     * @param {Event} ev
     */
    onDropdownShow(ev) {
        // If a dropdown inside the element 'this.hideEl' is clicked while the
        // header is fixed, we need to scroll the page up so that the
        // 'this.hideEl' element is no longer overflow hidden. Without
        // this, the dropdown would be invisible.
        if (this.cssAffixed) {
            ev.preventDefault();
            this.scrollingElement.scrollTo({ top: 0, behavior: "smooth" });
            this.dropdownClickedEl = ev.currentTarget;
        }
    }

    onSearchbarInput() {
        // Prevents the dropdown with search results from being hidden when the
        // header is fixed.
        // The scroll animation is instantaneous because the dropdown could open
        // before reaching the top of the page, which would result in an
        // incorrect calculated height of the header.
        if (this.cssAffixed) {
            this.scrollingElement.scroll({ top: 0 });
        }
    }

    onScroll() {
        super.onScroll();

        const scroll = this.scrollingElement.scrollTop;

        this.atTop = scroll <= this.topGap;
        this.isScrolled = scroll > this.topGap;

        // Need to be 'unfixed' when the window is not scrolled so that the
        // transparent menu option still works.
        if (scroll > this.topGap) {
            if (!this.cssAffixed) {
                this.transformShow();
                void this.el.offsetWidth; // Force a paint refresh
                this.toggleCSSAffixed(true);
            }
        } else {
            this.transformShow();
            void this.el.offsetWidth; // Force a paint refresh
            this.toggleCSSAffixed(false);
        }

        if (this.hideEl) {
            this.hideEl.style.height = "";
            this.hideEl.classList.remove("hidden");
            let elHeight = 0;
            if (this.cssAffixed) {
                // Close the dropdowns if they are open when scrolling.
                // Otherwise, the calculated height of the 'hideEl' element will
                // be incorrect because it will include the dropdown height.
                this.hideEl
                    .querySelectorAll(".dropdown-toggle.show")
                    .forEach((dropdownToggleEl) => {
                        Dropdown.getOrCreateInstance(dropdownToggleEl).hide();
                    });
                elHeight = this.hideEl.offsetHeight;
            } else {
                elHeight = this.hideEl.scrollHeight;
            }
            const scrollDelta = window.matchMedia(`(prefers-reduced-motion: reduce)`).matches
                ? scroll
                : Math.floor(scroll / 4);
            elHeight = Math.max(0, elHeight - scrollDelta);
            this.hideEl.classList.toggle("hidden", elHeight === 0);
            if (elHeight === 0) {
                this.hideEl.removeAttribute("style");
            } else {
                // When the page hasn't been scrolled yet, we don't set overflow
                // to hidden. Without this, the dropdowns would be invisible.
                // (e.g., "user menu" dropdown).
                this.hideEl.style.overflow = this.cssAffixed ? "hidden" : "";
                this.hideEl.style.height = this.cssAffixed ? `${elHeight}px` : "";
                let elPadding = parseInt(getComputedStyle(this.hideEl).paddingBlock);
                if (elHeight < elPadding * 2) {
                    const heightDifference = elPadding * 2 - elHeight;
                    elPadding = Math.max(0, elPadding - Math.floor(heightDifference / 2));
                    this.hideEl.style.setProperty("padding-block", `${elPadding}px`, "important");
                } else {
                    this.hideEl.style.paddingBlock = "";
                }
            }
            this.adaptToHeaderChange();
        }

        if (!this.cssAffixed && this.dropdownClickedEl) {
            const dropdown = Dropdown.getOrCreateInstance(this.dropdownClickedEl);
            dropdown.show();
            this.dropdownClickedEl = null;
        }

        if (this.isAnimated && this.transitionActive) {
            const scrollingDownward = scroll > this.position;
            this.position = scroll;
            if (this.scrollingDownward !== scrollingDownward) {
                this.checkpoint = scroll;
            }
            this.scrollingDownward = scrollingDownward;

            if (scrollingDownward) {
                const movement = this.position - this.checkpoint;
                if (this.isVisible && movement > this.scrollOffset + this.topGap) {
                    this.transformHide();
                }
            } else {
                const movement = this.checkpoint - this.position;
                if (!this.isVisible && movement > (this.scrollOffset + this.topGap) / 2) {
                    this.transformShow();
                }
            }
        }
    }
}

registry.category("public.interactions.edit").add("website.base_header_special", {
    Interaction: BaseHeaderSpecial,
    isAbstract: true,
});
