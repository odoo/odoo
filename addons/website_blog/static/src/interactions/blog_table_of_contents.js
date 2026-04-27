import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";
import { getScrollingElement, isScrollableY } from "@web/core/utils/scrolling";
import { utils as uiUtils, SIZES } from "@web/core/ui/ui_service";
import { scrollFixedOffset } from "@html_builder/utils/scrolling";

export class BlogTableOfContents extends Interaction {
    static selector = "#o_wblog_post_main";
    static selectorHas = ".o_wblog_toc";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _scrollingTarget: () => this.scrollingTarget,
    };
    dynamicContent = {
        _window: {
            "t-on-resize": this.debounced(this.onResize, 200),
        },
        _scrollingTarget: {
            "t-on-scroll": this.process,
        },
        ".o_wblog_toc": {
            "t-att-class": () => ({
                "d-none": !this.targets.length,
            }),
        },
    };

    setup() {
        this.navEl = this.el.querySelector(
            ".o_wblog_toc:not(.o_wblog_toc_mobile) .o_wblog_toc_nav"
        );
        this.navElMobile = this.el.querySelector(
            ".o_wblog_toc.o_wblog_toc_mobile .o_wblog_toc_nav"
        );
        this.contentEl = this.el.querySelector("#o_wblog_post_content .o_wblog_post_content_field");
        if (!this.navEl || !this.navElMobile || !this.contentEl) {
            return;
        }
        this.offsets = [];
        this.targets = [];
        this.activeTarget = null;

        this.isMobile = uiUtils.getSize() < SIZES.LG;
        this.scrollingElement = getScrollingElement(this.el.ownerDocument);
        this.scrollingTarget = isScrollableY(this.scrollingElement)
            ? this.scrollingElement
            : this.scrollingElement.ownerDocument.defaultView;
        this.scrollHeight = this.getScrollHeight();
    }

    start() {
        if (!this.navEl || !this.navElMobile || !this.contentEl) {
            return;
        }

        this.generateTOC();
    }

    getScrollHeight() {
        return (
            this.scrollingElement.scrollHeight ||
            Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)
        );
    }

    generateTOC() {
        const headingEls = this.contentEl.querySelectorAll("h1, h2, h3, h4, h5, h6");
        this.navEl.innerHTML = "";
        this.navElMobile.innerHTML = "";
        this.targets = [];
        if (!headingEls.length) {
            return;
        }

        const listGroupEl = document.createElement("div");
        listGroupEl.className = "list-group list-group-flush position-relative o_not_editable";
        listGroupEl.setAttribute("contenteditable", "false");
        // Track ancestor headings to derive a display level that never grows
        // by more than 1 between consecutive headings, regardless of the raw
        // h1..h6 jumps in the markup.
        const levelStack = [];
        // Ephemeral fallback ids for posts whose content pre-dates the
        // editor-time normalization. These are never persisted; once the post
        // is opened in the editor and saved the stable ids replace them.
        const usedIds = new Set();

        headingEls.forEach((headingEl, i) => {
            if (!headingEl.id || usedIds.has(headingEl.id)) {
                headingEl.id = `table_of_content_heading_1_${i + 1}`;
            }
            usedIds.add(headingEl.id);
            const htmlLevel = parseInt(headingEl.tagName[1]);
            while (levelStack.length && levelStack.at(-1).htmlLevel >= htmlLevel) {
                levelStack.pop();
            }
            const level = levelStack.length ? levelStack.at(-1).level + 1 : 0;
            levelStack.push({ htmlLevel, level });
            const linkEl = document.createElement("a");
            linkEl.href = `#${headingEl.id}`;
            linkEl.textContent = headingEl.textContent.trim();
            linkEl.className = `list-group-item list-group-item-action o_wblog_toc_link o_wblog_toc_link_${level} bg-transparent border-0 position-relative small`;
            linkEl.classList.add("o_not_editable");
            linkEl.setAttribute("contenteditable", "false");

            listGroupEl.appendChild(linkEl);
            this.targets.push(`#${headingEl.id}`);
        });

        const listGroupElMobile = listGroupEl.cloneNode(true);
        this.navEl.appendChild(listGroupEl);
        this.navElMobile.appendChild(listGroupElMobile);
        this.waitFor(this.services["public.interactions"].startInteractions(listGroupEl));
        this.waitFor(this.services["public.interactions"].startInteractions(listGroupElMobile));

        this.refreshOffsets();
    }

    refreshOffsets() {
        this.offsets = this.targets.map((target) => {
            const el = document.querySelector(target);
            return el ? el.getBoundingClientRect().top + window.scrollY : 0;
        });
    }

    process() {
        if (this.isMobile || !this.targets.length) {
            return;
        }

        const scrollTop = window.scrollY + scrollFixedOffset(this.el.ownerDocument) + 50;

        if (scrollTop < this.offsets[0]) {
            this.activate(this.targets[0]);
            return;
        }

        for (let i = this.offsets.length; i--; ) {
            if (scrollTop >= this.offsets[i]) {
                if (this.activeTarget !== this.targets[i]) {
                    this.activate(this.targets[i]);
                }
                return;
            }
        }
    }

    activate(target) {
        this.activeTarget = target;
        this.clear();
        const linkEl = this.navEl.querySelector(`[href="${target}"]`);
        if (linkEl) {
            linkEl.classList.add("active", "ps-3");
        }
    }

    clear() {
        for (const link of this.navEl.querySelectorAll(".list-group-item")) {
            link.classList.remove("active", "ps-3");
        }
    }

    onResize() {
        this.isMobile = uiUtils.getSize() < SIZES.LG;

        const scrollHeight = this.getScrollHeight();
        if (this.scrollHeight !== scrollHeight) {
            this.scrollHeight = scrollHeight;
            this.refreshOffsets();
            this.process();
        }
    }
}

registry.category("public.interactions").add("website_blog.toc", BlogTableOfContents);
