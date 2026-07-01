import { WebsiteBlogAlignment } from "./website_blog_alignment";
import { registry } from "@web/core/registry";

const WebsiteBlogAlignmentEdit = (I) =>
    class extends I {
        shouldStop() {
            // Should restart when targetWidthClass doesn't match the existing one.
            return this.targetWidthClass != this.getTargetWidthClass();
        }
        isImpactedBy(el) {
            // Potentially impacted by any content having a width class.
            // `.o_dirty` is required for the following reason. A normal blog
            // post content looks like this: `div.o_wblog_post_content_field` >
            // `section.s_text_block` > `div.o_container_small`. The first time
            // text width changes, `div.o_wblog_post_content_field` has to be
            // marked as dirty, thus it gets passed to `isImpactedBy` instead of
            // the element where width classes are actually applied. This means
            // that on the first width change (or preview) the interaction would
            // not restart. Catching `.o_dirty` fixes this problem.
            const widthSelector = [...WebsiteBlogAlignment.widthClasses, ".o_dirty"].join(", ");
            return this.el.contains(el) && el.matches(widthSelector);
        }
    };

registry.category("public.interactions.edit").add("website_blog.website_blog_alignment", {
    Interaction: WebsiteBlogAlignment,
    mixin: WebsiteBlogAlignmentEdit,
});
