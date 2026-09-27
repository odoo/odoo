import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";

/**
 * Extracts the numeric heading id encoded in a blog post heading element id
 * (`blog_table_of_content_<headingId>`).
 *
 * @param {HTMLElement} headingEl
 * @returns {Number}
 */
function getHeadingId(headingEl) {
    const id = headingEl.getAttribute("id");
    if (id && id.startsWith("blog_table_of_content_")) {
        return parseInt(id.slice(22));
    }
    return 0;
}

/**
 * Builder option component for blog index pages (both "All blogs" and specific
 * blog pages).
 */
export class BlogPostPageOption extends BaseOptionComponent {
    static id = "blog_post_page_option";
    static template = "website_blog.blogPostPageOption";

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            // True when viewing a specific blog page, allows to show some
            // options not needed on the "All blogs" page (detected via the
            // `o_wblog_single_blog_top` class, only added on specific blogs).
            isOnBlogPage: !!el.querySelector(".o_wblog_single_blog_top"),
        }));
    }
}

export class BlogPostPageOptionPlugin extends Plugin {
    static id = "blogPostPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        normalize_processors: this.normalize.bind(this),
        dropzone_selectors: {
            selector: ".s_table_of_content",
            excludeAncestor: ".o_wblog_post_content_field",
        },
    };

    normalize(rootEl) {
        const blogContentEl = rootEl.closest(".o_wblog_post_content_field");
        if (blogContentEl) {
            this.assignHeadingIds(blogContentEl);
        }
        return rootEl;
    }

    /**
     * Assigns a stable id to every heading in the blog post content so that
     * the public TOC interaction can build deep-link anchors without mutating
     * the DOM at runtime. Existing valid ids are preserved across saves;
     * duplicates and missing ids are reassigned from a running max.
     *
     * @param {HTMLElement} contentEl
     */
    assignHeadingIds(contentEl) {
        // Remove stale TOC ids from non-heading elements (e.g. a heading converted
        // back to a paragraph
        for (const el of contentEl.querySelectorAll("[id^='blog_table_of_content_']")) {
            if (!el.matches("h1, h2, h3, h4, h5, h6")) {
                el.removeAttribute("id");
                el.removeAttribute("data-anchor");
            }
        }
        const headingEls = [...contentEl.querySelectorAll("h1, h2, h3, h4, h5, h6")];
        let maxHeadingId = Math.max(0, ...headingEls.map(getHeadingId));
        const seenIds = new Set();
        for (const headingEl of headingEls) {
            let headingId = getHeadingId(headingEl);
            if (headingId && seenIds.has(headingId)) {
                headingId = 0;
            }
            if (!headingId) {
                maxHeadingId += 1;
                headingId = maxHeadingId;
            }
            seenIds.add(headingId);
            headingEl.setAttribute("id", `blog_table_of_content_${headingId}`);
            if (headingEl.dataset.anchor === undefined) {
                headingEl.dataset.anchor = "true";
            }
        }
    }
}

registry.category("website-options").add(BlogPostPageOption.id, BlogPostPageOption);
registry.category("website-plugins").add(BlogPostPageOptionPlugin.id, BlogPostPageOptionPlugin);
