import { applyFunDependOnSelectorAndExclude } from "@html_builder/plugins/utils";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { rpc } from "@web/core/network/rpc";

/**
 * Extracts the numeric heading id encoded in a blog post heading element id
 * (`blog_table_of_content_<headingId>`).
 */
function getHeadingId(headingEl) {
    const match = /^blog_table_of_content_(\d+)$/.exec(
        headingEl && headingEl.getAttribute("id")
    );
    return match ? parseInt(match[1]) : 0;
}

/**
 * Builder option component for blog index pages (both all-blogs homepage and
 * specific blog pages).
 *
 * `isOnBlogPage` is true when the page belongs to a specific blog
 * (detected via `.o_wblog_homepage_top` which is only rendered when `blog` is
 * set in the QWeb context). It drives which variant of the Style / Content
 * Width options is shown in the panel:
 *   - false → global websiteConfig (ir.ui.view toggles, affect all blogs)
 *   - true  → per-blog classAction (CSS class on #o_wblog_index_content,
 *              persisted to blog.blog_layout / blog.blog_page_container on save)
 */
export class BlogPostPageOption extends BaseOptionComponent {
    static id = "blog_post_page_option";
    static template = "website_blog.blogPostPageOption";

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            // True when viewing a specific blog page (blog variable set in QWeb).
            isOnBlogPage: !!el.querySelector('.o_wblog_homepage_top'),
        }));
    }
}

registry.category("website-options").add(BlogPostPageOption.id, BlogPostPageOption);

export class BlogPostPageOptionPlugin extends Plugin {
    static id = "blogPostPageOption";
    /** @type {import("plugins").WebsiteResources} */
    resources = {
        // Called by SavePlugin when the user saves the page.
        on_ready_to_save_document_handlers: this.onSave.bind(this),
        normalize_processors: this.normalize.bind(this),
        dropzone_selectors: {
            selector: ".s_table_of_content",
            excludeAncestor: ".o_wblog_post_content_field",
        },
    };

    normalize(root) {
        applyFunDependOnSelectorAndExclude(this.assignHeadingIds.bind(this), root, {
            selector: ".o_wblog_post_content_field",
        });
    }

    /**
     * Assigns a stable id to every heading in the blog post content so that
     * the public TOC interaction can build deep-link anchors without mutating
     * the DOM at runtime. Existing valid ids are preserved across saves;
     * duplicates and missing ids are reassigned from a running max.
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

    /**
     * Persist per-blog display settings to the blog.blog model via /blog/config.
     *
     * The builder stores the user's choices as CSS classes on #o_wblog_index_content:
     *   - o_wblog_post_opt_layout_<value>  → blog.blog_layout
     *   - o_wblog_post_opt_container_fluid → blog.blog_page_container = 'fluid'
     *
     * This handler runs on every save but is a no-op on the all-blogs homepage
     * (data-blog-id is empty there; global layout is handled by websiteConfig).
     */
    async onSave() {
        const indexEl = this.editable.querySelector("#o_wblog_index_content");
        if (!indexEl) {
            return;
        }
        // data-blog-id is set by the QWeb template only on specific blog pages.
        const blogId = parseInt(indexEl.dataset.blogId || "0");
        if (!blogId) {
            // All-blogs homepage: layout is managed globally via websiteConfig.
            return;
        }
        // Extract layout: find the single o_wblog_post_opt_layout_* class and
        // strip the prefix to get the field value (e.g. "list", "grid", …).
        // Returns false when no class is present (= remove the per-blog override).
        const layoutClass = Array.from(indexEl.classList).find((cls) =>
            cls.startsWith("o_wblog_post_opt_layout_")
        );
        const blogLayout = layoutClass
            ? layoutClass.replace("o_wblog_post_opt_layout_", "")
            : false;
        // Extract container width: binary flag, no prefix stripping needed.
        const blogPageContainer = indexEl.classList.contains("o_wblog_post_opt_container_fluid")
            ? "fluid"
            : false;
        await rpc("/blog/config", {
            blog_id: blogId,
            blog_layout: blogLayout,
            blog_page_container: blogPageContainer,
        });
    }
}

registry.category("website-plugins").add(BlogPostPageOptionPlugin.id, BlogPostPageOptionPlugin);
