import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

import { isBrowserSafari } from "@web/core/browser/feature_detection";
import { browser } from "@web/core/browser/browser";
import { verifyHttpsUrl } from "@website/utils/misc";

export class SearchBarResults extends Interaction {
    static selector = ".o_searchbar_form .o_dropdown_menu";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _scrollingParent: () => this.scrollingParentEl,
        _searchbar: () => this.searchBarEl,
    };
    dynamicContent = {
        _root: {
            "t-att-style": () => {
                const bcr = this.searchBarEl.getBoundingClientRect();
                return {
                    position: "absolute !important",
                    "max-width": `${bcr.width}px !important`,
                    "max-height": `max(40vh, ${
                        document.body.clientHeight - bcr.bottom - 16
                    }px) !important`,
                    "min-width": this.autocompleteMinWidth,
                };
            },
            "t-att-class": () => ({
                show: true,
            }),
            "t-att-data-bs-popper": () => (this.isDropup ? "" : undefined),
        },
        _searchbar: {
            "t-att-class": () => ({
                dropup: this.isDropup,
            }),
        },
        _window: {
            "t-on-resize": () => {}, // Re-apply _root:t-att-style.
        },
        _scrollingParent: {
            "t-on-scroll": () => {}, // Re-apply _root:t-att-style.
        },
        ".dropdown-item": {
            "t-on-mousedown": this.onMousedown,
            "t-on-mouseup": this.onMouseup,
            "t-on-keydown": this.onKeydown,
        },
        "button.extra_link": {
            "t-on-click.prevent": this.onExtraLinkClick,
        },
        ".s_searchbar_fuzzy_submit": {
            "t-on-click.prevent": (event) => {
                this.inputEl.value = event.target.textContent;
                const formEl = this.searchBarEl.querySelector(".o_search_order_by").closest("form");
                formEl.submit();
            },
        },
    };
    autocompleteMinWidth = 300;

    setup() {
        this.searchBarEl = this.el.closest(".o_searchbar_form");
        this.inputEl = this.searchBarEl.querySelector(".search-query");
        this.scrollingParentEl = null;

        // Handle the case where the searchbar is in a mega menu by making
        // it position:fixed and forcing its size. Note: this could be the
        // default behavior or at least needed in more cases than the mega
        // menu only (all scrolling parents). But as a stable fix, it was
        // easier to fix that case only as a first step, especially since
        // this cannot generically work on all scrolling parent.
        const megaMenuEl = this.searchBarEl.closest(".o_mega_menu");
        if (megaMenuEl) {
            const navbarEl = this.searchBarEl.closest(".navbar");
            const navbarTogglerEl = navbarEl ? navbarEl.querySelector(".navbar-toggler") : null;
            if (navbarTogglerEl && navbarTogglerEl.clientWidth < 1) {
                this.scrollingParentEl = megaMenuEl;
            }
        }

        // Adjust the menu's position based on the scroll height.
        this.isDropup = false;
        if (this.el.getBoundingClientRect().bottom > document.documentElement.offsetHeight) {
            // If the menu overflows below the page, we reduce its height.
            this.el.style.overflowY = "auto";
            // We then recheck if the menu still overflows below the page.
            if (this.el.getBoundingClientRect().bottom > document.documentElement.offsetHeight) {
                // If the menu still overflows below the viewport after its
                // height has been reduced, we position it where most space is
                // available
                const searchPosition = this.searchBarEl.getBoundingClientRect();
                this.isDropup =
                    searchPosition.top >
                    document.documentElement.offsetHeight - searchPosition.bottom;
            }
        }
    }

    onMousedown() {
        // On Safari, links and buttons are not focusable by default. We need
        // to get around that behavior to avoid onFocusOut() from triggering
        // render(), as this would prevent the click from working.
        if (isBrowserSafari) {
            this.searchBarEl.dispatchEvent(
                new CustomEvent("safarihack", { detail: { linkHasFocus: true } })
            );
        }
    }

    onMouseup() {
        // See comment in onMousedown.
        if (isBrowserSafari) {
            this.searchBarEl.dispatchEvent(
                new CustomEvent("safarihack", { detail: { linkHasFocus: false } })
            );
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    onKeydown(ev) {
        switch (ev.key) {
            case "ArrowUp":
            case "ArrowDown": {
                ev.preventDefault();
                const focusableEls = [this.inputEl, ...this.el.children];
                const focusedEl = document.activeElement;
                const currentIndex = focusableEls.indexOf(focusedEl) || 0;
                const delta = ev.key === "ArrowUp" ? focusableEls.length - 1 : 1;
                const nextIndex = (currentIndex + delta) % focusableEls.length;
                const nextFocusedEl = focusableEls[nextIndex];
                nextFocusedEl.focus();
                break;
            }
        }
    }

    /**
     * @param {PointerEvent} ev
     */
    onExtraLinkClick(ev) {
        browser.location.href = verifyHttpsUrl(ev.currentTarget.dataset.target);
    }
}

registry.category("public.interactions").add("website.search_bar_results", SearchBarResults);
