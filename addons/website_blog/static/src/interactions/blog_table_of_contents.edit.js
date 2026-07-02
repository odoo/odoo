import { BlogTableOfContents } from "./blog_table_of_contents";
import { registry } from "@web/core/registry";

const BlogTableOfContentsEdit = (I) =>
    class extends I {
        isImpactedBy(el) {
            return el.matches(".o_wblog_post_content_field");
        }
        getConfigurationSnapshot() {
            const headingEls = [...this.contentEl.querySelectorAll("h1, h2, h3, h4, h5, h6")];
            const headingTexts = headingEls.map((el) => el.textContent);
            const headingSizes = headingEls.map((el) => el.tagName);
            return JSON.stringify({ texts: headingTexts, sizes: headingSizes });
        }
    };

registry.category("public.interactions.edit").add("website_blog.toc", {
    Interaction: BlogTableOfContents,
    mixin: BlogTableOfContentsEdit,
});
