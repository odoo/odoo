import { registry } from "@web/core/registry";
import { BlogTableOfContents } from "./blog_table_of_contents";

const BlogTableOfContentsEdit = (I) =>
    class extends I {
        isImpactedBy(el) {
            return el.closest(".o_wblog_post_content_field");
        }
        getConfigurationSnapshot() {
            let snapshot = super.getConfigurationSnapshot();
            snapshot = JSON.parse(snapshot || "{}");

            const headingEls = [...this.contentEl.querySelectorAll("h1, h2, h3, h4, h5, h6")];
            const headingTexts = headingEls.map((el) => el.textContent);
            const headingSizes = headingEls.map((el) => el.tagName);

            snapshot.texts = headingTexts;
            snapshot.sizes = headingSizes;
            return JSON.stringify(snapshot);
        }
    };

registry.category("public.interactions.edit").add("website_blog.toc", {
    Interaction: BlogTableOfContents,
    mixin: BlogTableOfContentsEdit,
});
