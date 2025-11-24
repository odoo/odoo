import { WebsiteBlogAlignment } from "./website_blog_alignment";
import { registry } from "@web/core/registry";

const WebsiteBlogAlignmentEdit = (I) =>
    class extends I {
        shouldStop() {
            // Should always restart, because each option may modify the width of
            // the element, meaning the interaction needs to recompute.
            return true;
        }
        isImpactedBy(el) {
            // Any content inside having a width class - or first modification.
            const widthSelector = ".o_dirty, ." + WebsiteBlogAlignment.widthClasses.join(", .");
            return this.el.contains(el) && el.matches(widthSelector);
        }
    };

registry.category("public.interactions.edit").add("website_blog.website_blog_alignment", {
    Interaction: WebsiteBlogAlignment,
    mixin: WebsiteBlogAlignmentEdit,
});
