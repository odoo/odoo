import { batched, proxy } from "@odoo/owl";
import { closestScrollableY, scrollTo } from "@web/core/utils/scrolling";

export const HEADINGS = ["H1", "H2", "H3", "H4", "H5", "H6"];

export class TableOfContentManager {
    constructor(containerRef) {
        this.containerRef = containerRef;
        this.structure = proxy({
            headings: [],
            isNew: true,
        });
        this.batchedUpdateStructure = batched(this.updateStructure.bind(this));
    }

    getContainerEl() {
        return this.containerRef.el;
    }

    /**
     * Allows to fetch relevant headings in the page when building the Table of Content.
     * Will filter out things we don't want:
     * - Empty headers
     * - Headers only containing the 'ZeroWidthSpace' element ('\u200B')
     * - Headers descendants of an element with `data-embedded`
     *
     * @param {Element} element
     */
    fetchValidHeadings(element) {
        const inEmbeddedHeadings = new Set(
            element.querySelectorAll(
                HEADINGS.map((heading) => `[data-embedded] ${heading}`).join(",")
            )
        );
        return Array.from(element.querySelectorAll(HEADINGS.join(",")))
            .filter((heading) => heading.innerText.trim().replaceAll("\u200B", "").length > 0)
            .filter((heading) => !inEmbeddedHeadings.has(heading));
    }

    scrollIntoView(heading) {
        if (!heading) {
            return;
        }
        const { target } = heading;
        let offset = 0;
        const scrollable = closestScrollableY(target);
        for (const el of scrollable.children) {
            const { position, top, height } = getComputedStyle(el);
            if (position === "sticky" && parseInt(top) === 0) {
                offset = Math.max(offset, parseInt(height));
            }
        }
        scrollTo(target, { behavior: "smooth", offset: -offset }).then(() => {
            // Scroll again in case we actually went downwards.
            scrollTo(target, { behavior: "smooth" });
        });
        target.classList.add("o_embedded_toc_header_highlight");
        window.setTimeout(() => {
            target.classList.remove("o_embedded_toc_header_highlight");
        }, 2000);
    }

    updateStructure() {
        const container = this.getContainerEl();
        if (!container) {
            return;
        }
        const tagDepthStack = [];
        this.structure.headings = this.fetchValidHeadings(container).map((heading) => {
            while (tagDepthStack.at(-1) >= heading.tagName) {
                tagDepthStack.pop();
            }
            const depth = tagDepthStack.length;
            tagDepthStack.push(heading.tagName);
            return {
                depth,
                name: heading.innerText,
                target: heading,
            };
        });
        this.structure.isNew = false;
    }
}
