import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteBlogAlignment extends Interaction {
    static widthClasses = [".o_container_small", ".container", ".container-fluid"];

    static selector = ".website_blog";
    dynamicContent = {
        ".o_container_as_first": {
            "t-att-class": () => ({
                o_container_as_first: false,
                o_container_small: this.targetWidthClass === ".o_container_small",
                container: this.targetWidthClass === ".container",
                "container-fluid": this.targetWidthClass === ".container-fluid",
            }),
        },
    };

    setup() {
        this.targetWidthClass = this.getTargetWidthClass();
    }

    /**
     * Finds and returns the width class of the main content in the blog post.
     *
     * By default the content is a text block (`section.s_text_block`), but the
     * code targets the first `section` element (not necessary `.s_text_block`)
     * to cover for cases where the user switched the text with other content.
     *
     * @returns {String} the width class if found, "container-fluid" otherwise
     */
    getTargetWidthClass() {
        const blogPostContentEl = this.el.querySelector(".o_wblog_post_content_field > section");
        if (!blogPostContentEl) {
            return "container-fluid";
        }
        const targetClass = WebsiteBlogAlignment.widthClasses.find((cls) =>
            blogPostContentEl.querySelector(cls)
        );
        return targetClass;
    }
}

registry
    .category("public.interactions")
    .add("website_blog.website_blog_alignment", WebsiteBlogAlignment);
