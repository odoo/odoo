import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";
import { patch } from "@web/core/utils/patch";
import { isVisible } from "@web/core/utils/ui";

import { closestScrollableY, isScrollableY } from "@web/core/utils/scrolling";
import { AnchorSlide } from "@website/interactions/anchor_slide";

const CLASS_NAME_DROPDOWN_ITEM = "dropdown-item";
const CLASS_NAME_ACTIVE = "active";
const SELECTOR_NAV_LIST_GROUP = ".nav, .list-group";
const SELECTOR_NAV_LINKS = ".nav-link";
const SELECTOR_NAV_ITEMS = ".nav-item";
const SELECTOR_LIST_ITEMS = ".list-group-item";
const SELECTOR_LINK_ITEMS = `${SELECTOR_NAV_LINKS}, ${SELECTOR_LIST_ITEMS}, .${CLASS_NAME_DROPDOWN_ITEM}`;
const SELECTOR_DROPDOWN = ".dropdown";
const SELECTOR_DROPDOWN_TOGGLE = ".dropdown-toggle";

const getSelector = element => {
    let hrefAttr = element.getAttribute("href");
    if (!hrefAttr || !hrefAttr.startsWith("#")) {
        return null;
    }
    const selector = hrefAttr && hrefAttr !== "#" ? hrefAttr.trim() : null;
    return selector;
};

const parents = (element, selector) => {
    const parents = [];
    let ancestor = element.parentNode.closest(selector);
    while (ancestor) {
        parents.push(ancestor);
        ancestor = ancestor.parentNode.closest(selector);
    }
    return parents;
};

const prev = (element, selector) => {
    let previous = element.previousElementSibling;
    while (previous) {
        if (previous.matches(selector)) {
            return [previous];
        }
        previous = previous.previousElementSibling;
    }
    return [];
};

export class TableOfContent extends Interaction {
    static selector = "section .s_table_of_content_navbar_sticky";
    dynamicContent = {
    };

    setup() {
        this.scrollBound = this.process.bind(this);
        this.offsets = [];
        this.targets = [];
        this.activeTarget = null;
        this.scrollHeight = 0;
        this.offset = 0;

        this.stripNavbarStyles();
        this.scrollElement = closestScrollableY(this.el.closest(".s_table_of_content")) || this.el.ownerDocument.scrollingElement;
        this.scrollTarget = isScrollableY(this.scrollElement) ? this.scrollElement : this.scrollElement.ownerDocument.defaultView;
        this.tocElement = this.el.querySelector(".s_table_of_content_navbar");
        this.previousPosition = -1;
        this.updateTableOfContentNavbarPosition();

        this.registerCleanup(this.services.website_menus.registerCallback(this.updateTableOfContentNavbarPosition.bind(this)));
    }

    start() {
        this.addListener(this.scrollTarget, "scroll", this.scrollBound);
    }

    destroy() {
        this.el.style.top = "";
        const navbarEl = this.el.querySelector(".s_table_of_content_navbar");
        if (navbarEl) {
            navbarEl.style.top = "";
            navbarEl.style.maxHeight = "";
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    stripNavbarStyles() {
        // This is needed for styles added on translations when the master text
        // has no style.
        for (let el of this.el.querySelectorAll(".s_table_of_content_navbar .table_of_content_link")) {
            const translationEl = el.querySelector("span[data-oe-translation-state]");
            if (translationEl) {
                el = translationEl;
            }
            const text = el.textContent; // Get text from el.
            el.textContent = text; // Replace all of el's content with that text.
        }
    }
    updateTableOfContentNavbarPosition() {
        if (!this.el.querySelector("a.table_of_content_link")) {
            // Do not start the scrollspy if the TOC is empty.
            return;
        }
        let position = 0;
        for (const el of this.el.ownerDocument.querySelectorAll(".o_top_fixed_element")) {
            position += el.getBoundingClientRect().bottom;
        }
        const isHorizontalNavbar = this.el.classList.contains("s_table_of_content_horizontal_navbar");
        this.el.style.top = isHorizontalNavbar ? `${position}px` : "";
        const navbarEl = this.el.querySelector(".s_table_of_content_navbar");
        navbarEl && (navbarEl.style.top = isHorizontalNavbar ? "" : `${position + 20}px`);
        position += isHorizontalNavbar ? this.el.getBoundingClientRect().height : 0;
        navbarEl && (navbarEl.style.maxHeight = isHorizontalNavbar ? "" : `calc(100vh - ${position + 40}px)`);
        if (this.previousPosition !== position) {
            this.offset = position + 100;
            this.refresh();
            this.process();
            this.previousPosition = position;
        }
    }

    getScrollHeight() {
        return this.scrollElement.scrollHeight || Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    }

    refresh() {
        this.offsets = [];
        this.targets = [];
        this.scrollHeight = this.getScrollHeight();
        const targets = [...this.tocElement.querySelectorAll(SELECTOR_LINK_ITEMS)];
        targets.map(element => {
            const targetSelector = getSelector(element);
            const target = targetSelector ? document.querySelector(targetSelector) : null;
            if (target) {
                const targetBCR = target.getBoundingClientRect();

                if (targetBCR.width || targetBCR.height) {
                    return [targetBCR.top, targetSelector];
                }
            }
            return null;
        }).filter(item => item).sort((a, b) => a[0] - b[0]).forEach(item => {
            this.offsets.push(item[0]);
            this.targets.push(item[1]);
        });
        const baseScrollTop = this.scrollElement.scrollTop;
        for (let i = 0; i < this.offsets.length; i++) {
            this.offsets[i] += baseScrollTop;
        }
    }

    activate(target) {
        const element = document.querySelector(`[href="${target}"]`);
        if (!element || !isVisible(element)) {
            return;
        }
        this.activeTarget = target;
        this.clear();
        const queries = SELECTOR_LINK_ITEMS.split(",").map(selector => `${selector}[href="${target}"]`);
        const link = this.tocElement.querySelector(queries.join(","));
        link.classList.add(CLASS_NAME_ACTIVE);
        if (link.classList.contains(CLASS_NAME_DROPDOWN_ITEM)) {
            link.closest(SELECTOR_DROPDOWN).querySelector(SELECTOR_DROPDOWN_TOGGLE).classList.add(CLASS_NAME_ACTIVE);
        } else {
            parents(link, SELECTOR_NAV_LIST_GROUP).forEach(listGroup => {
                // Set triggered links parents as active
                // With both <ul> and <nav> markup a parent is the previous sibling of any nav ancestor
                prev(listGroup, `${SELECTOR_NAV_LINKS}, ${SELECTOR_LIST_ITEMS}`).forEach(item => item.classList.add(CLASS_NAME_ACTIVE)); // Handle special case when .nav-link is inside .nav-item
                prev(listGroup, SELECTOR_NAV_ITEMS).forEach(navItem => {
                    [...navItem.children].filter(child => child.matches(SELECTOR_NAV_LINKS)).forEach(item => item.classList.add(CLASS_NAME_ACTIVE));
                });
            });
        }
    }

    clear() {
        [...this.tocElement.querySelectorAll(SELECTOR_LINK_ITEMS)].filter(node => node.classList.contains(CLASS_NAME_ACTIVE)).forEach(node => node.classList.remove(CLASS_NAME_ACTIVE));
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    process() {
        const scrollTop = this.scrollElement.scrollTop + this.offset;
        const scrollHeight = this.getScrollHeight();
        const maxScroll = this.offset + scrollHeight - this.scrollElement.getBoundingClientRect().height;
        if (this.scrollHeight !== scrollHeight) {
            this.refresh();
        }
        if (scrollTop >= maxScroll) {
            const target = this.targets[this.targets.length - 1];
            if (this.activeTarget !== target) {
                this.activate(target);
            }
            return;
        }
        if (this.activeTarget && scrollTop < this.offsets[0] && this.offsets[0] > 0) {
            this.activeTarget = null;
            this.clear();
        } else {
            for (let i = this.offsets.length; i--;) {
                const isActiveTarget = this.activeTarget !== this.targets[i] && scrollTop >= this.offsets[i] && (typeof this.offsets[i + 1] === "undefined" || scrollTop < this.offsets[i + 1]);

                if (isActiveTarget) {
                    this.activate(this.targets[i]);
                }
            }
        }
        if (this.activeTarget === null) {
            this.activate(this.targets[0]);
        }
    }
}

patch(AnchorSlide.prototype, {
    /**
     * Overridden to add the height of the horizontal sticky navbar at the scroll value
     * when the link is from the table of content navbar
     *
     * @override
     */
    computeExtraOffset() {
        let extraOffset = super.computeExtraOffset(...arguments);
        if (this.el.classList.contains("table_of_content_link")) {
            const tableOfContentNavbarEl = this.el.closest(".s_table_of_content_navbar_sticky.s_table_of_content_horizontal_navbar");
            if (tableOfContentNavbarEl) {
                extraOffset += tableOfContentNavbarEl.getBoundingClientRect().height;
            }
        }
        return extraOffset;
    },
});

registry
    .category("public.interactions")
    .add("website.table_of_content", TableOfContent);

registry
    .category("public.interactions.edit")
    .add("website.table_of_content", { Interaction: TableOfContent });
