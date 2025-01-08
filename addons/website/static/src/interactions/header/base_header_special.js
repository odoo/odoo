import { BaseHeader } from "@website/interactions/header/base_header";
import { registry } from "@web/core/registry";

export class BaseHeaderSpecial extends BaseHeader {
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _dropdown: () => this.hideEl?.querySelector(".dropdown-toggle"),
        _searchbar: () => this.searchbarEl,
    };
    dynamicContent = {
        ...this.dynamicContent,
        _dropdown: {
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
        const scroll = this.scrollingElement.scrollTop;

        this.atTop = (scroll <= this.topGap);
        this.isScrolled = (scroll > this.topGap);

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

        this.el.style.setProperty("transition", (this.hideEl && scroll < this.hideElHeight) && this.transitionActive ? "none" : "");

        if (this.isVisible && this.hideEl) {
            this.forcedScroll = Math.min(scroll, this.hideElHeight);
            this.el.style.transform = this.atTop ? "" : `translate(0, -${this.forcedScroll + this.topGap}px)`;
        }

        if (!this.cssAffixed && this.dropdownClickedEl) {
            const dropdown = Dropdown.getOrCreateInstance(this.dropdownClickedEl);
            dropdown.show();
            this.dropdownClickedEl = null;
        }

        if (this.isAnimated && this.transitionActive) {
            const scrollingDownward = (scroll > this.position);
            this.position = scroll;
            if (this.scrollingDownward !== scrollingDownward) {
                this.checkpoint = scroll;
            }
            this.scrollingDownward = scrollingDownward;

            if (scrollingDownward) {
                if (this.isVisible && (this.position - this.checkpoint) > (this.scrollOffset + this.topGap)) {
                    this.transformHide();
                }
            } else {
                if (!this.isVisible && (this.checkpoint - this.position) > ((this.scrollOffset + this.topGap) / 2)) {
                    this.transformShow();
                }
            }
        }
    }
}

registry
    .category("public.interactions.edit")
    .add("website.base_header_special", {
        Interaction: BaseHeaderSpecial,
        isAbstract: true,
    });
