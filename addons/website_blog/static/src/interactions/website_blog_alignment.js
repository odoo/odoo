import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class WebsiteBlogAlignment extends Interaction {
    static widthClasses = ["o_container_small", "container", "container-fluid"];

    static selector = ".website_blog";
    dynamicContent = {
        ".o_container_as_first": {
            "t-att-class": () => ({
                o_container_as_first: false,
                o_container_small: this.targetClass === "o_container_small",
                container: this.targetClass === "container",
                "container-fluid": this.targetClass === "container-fluid",
            }),
        },
    };

    setup() {
        this.targetClass = this.getTargetWidthClass();
    }

    getTargetWidthClass() {
        const blogPostContentEl = this.el.querySelector(".o_wblog_post_content_field");
        if (!blogPostContentEl) {
            return;
        }

        let targetClass = "o_container_small";
        for (const extraSelector of [".s_text_block ", ":first-of-type", ":first-of-type "]) {
            const selector = WebsiteBlogAlignment.widthClasses.map(
                (cls) => `section${extraSelector}.${cls}`
            );
            const source = blogPostContentEl.querySelector(selector);
            if (source) {
                targetClass = WebsiteBlogAlignment.widthClasses.find((cls) =>
                    source.classList.contains(cls)
                );
                break;
            }
        }
        return targetClass;
    }
}

registry
    .category("public.interactions")
    .add("website_blog.website_blog_alignment", WebsiteBlogAlignment);
