import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { patch } from "@web/core/utils/patch";
import { closestScrollableY, isScrollableY } from "@web/core/utils/scrolling";
import { isVisible } from "@web/core/utils/ui";
import { AnchorSlide } from "@website/interactions/anchor_slide";

const getSelector = element => {
    let hrefAttr = element.getAttribute("href");
    if (!hrefAttr?.startsWith("#")) {
        return null;
    }
    return hrefAttr !== "#" ? hrefAttr.trim() : null;
};

const parents = (element, selector) => {
    const parents = [];
    let ancestor = element.parentElement.closest(selector);
    while (ancestor) {
        parents.push(ancestor);
        ancestor = ancestor.parentElement.closest(selector);
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
        _root: {
            "t-att-style": () => ({
                "top": this.isHorizontal ? `${this.position}px` : undefined,
            }),
        },
        ".s_table_of_content_navbar": {
            "t-att-style": () => ({
                "top": this.isHorizontal ? undefined : `${this.position}px`,
                "maxHeight": this.isHorizontal ? undefined : `calc(100vh - ${this.position + 40}px)`,
            }),
        },
    };

    setup() {
        this.position = 20;
        this.isHorizontal = this.el.classList.contains("s_table_of_content_horizontal_navbar");

        this.scrollBound = this.process.bind(this);
        this.offsets = [];
        this.targets = [];
        this.activeTarget = null;
        this.scrollHeight = 0;
        this.offset = 0;

        this.scrollElement = closestScrollableY(this.el.closest(".s_table_of_content")) || this.el.ownerDocument.scrollingElement;
        this.scrollTarget = isScrollableY(this.scrollElement) ? this.scrollElement : this.scrollElement.ownerDocument.defaultView;
        this.tocElement = this.el.querySelector(".s_table_of_content_navbar");
        this.previousPosition = -1;
    }

    start() {
        this.updateTableOfContentNavbarPosition();
        this.registerCleanup(this.services.website_menus.registerCallback(this.updateTableOfContentNavbarPosition.bind(this)));

        this.addListener(this.scrollTarget, "scroll", this.scrollBound);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    updateTableOfContentNavbarPosition() {
        if (!this.el.querySelector("a.table_of_content_link")) {
            // Do not start the scrollspy if the TOC is empty.
            return;
        }

        let position = this.isHorizontal ? 0 : 20;
        for (const el of this.el.ownerDocument.querySelectorAll(".o_top_fixed_element")) {
            position += el.getBoundingClientRect().bottom;
        }

        this.position = position;
        position += (this.isHorizontal ? this.el.offsetHeight : 0);

        if (this.previousPosition !== position) {
            this.offset = position + 100;
            this.refresh();
            this.process();
            this.previousPosition = position;
        }
        this.updateContent();
    }

    getScrollHeight() {
        return this.scrollElement.scrollHeight || Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
    }

    refresh() {
        this.offsets = [];
        this.targets = [];
        this.scrollHeight = this.getScrollHeight();
        const targets = [...this.tocElement.querySelectorAll(".nav-link, .list-group-item, .dropdown-item")];
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

    /**
     * @param {string} target
     */
    activate(target) {
        const element = document.querySelector(`[href="${target}"]`);
        if (!element || !isVisible(element)) {
            return;
        }
        this.activeTarget = target;
        this.clear();
        const queries = ".nav-link, .list-group-item, .dropdown-item".split(",").map(selector => `${selector}[href="${target}"]`);
        const link = this.tocElement.querySelector(queries.join(","));
        link.classList.add("active");
        if (link.classList.contains("dropdown-item")) {
            link.closest(".dropdown").querySelector(".dropdown-toggle").classList.add("active");
        } else {
            const listGroupEls = parents(link, ".nav, .list-group");
            for (const listGroupEl of listGroupEls) {
                // Set triggered links parents as active
                // With both <ul> and <nav> markup a parent is the previous sibling of any nav ancestor
                const itemEls = prev(listGroupEl, ".nav-link, .list-group-item");
                for (const itemEl of itemEls) {
                    itemEl.classList.add("active")
                }
                // Handle special case when .nav-link is inside .nav-item
                const navItemEls = prev(listGroupEl, ".nav-item");
                for (const navItemEl of navItemEls) {
                    for (const childEl of navItemEl.children) {
                        if (childEl.matches(".nav-link")) {
                            childEl.classList.add("active")
                        }
                    }
                }
            }
        }
    }

    clear() {
        const itemEls = this.tocElement.querySelectorAll(".nav-link, .list-group-item, .dropdown-item");
        for (const itemEl of itemEls) {
            itemEl.classList.remove("active");
        }
    }

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
                const isActiveTarget =
                    this.activeTarget !== this.targets[i]
                    && scrollTop >= this.offsets[i]
                    && (typeof this.offsets[i + 1] === "undefined"
                        || scrollTop < this.offsets[i + 1]);

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
