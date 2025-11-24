import { registry } from "@web/core/registry";
import { clickOnEditAndWaitEditMode, clickOnSave } from "@website/js/tours/tour_utils";

function checkBlogElements(className) {
    return [
        {
            content: `Ensure breadcrumb element is correctly aligned with text block (${className})`,
            trigger: `:iframe div#o_wblog_post_content > nav.${className}`,
        },
        {
            content: `Ensure post_info element is correctly aligned with text block (${className})`,
            trigger: `:iframe div#o_wblog_post_info.${className}`,
        },
        {
            content: `Ensure tags element is correctly aligned with text block (${className})`,
            trigger: `:iframe div#o_wblog_post_tags.${className}`,
        },
        {
            content: `Ensure comment element is correctly aligned with text block (${className})`,
            trigger: `:iframe div.${className} > div > div#o_wblog_post_comments`,
        },
    ];
}

registry.category("web_tour.tours").add("blog_post_page_horizontal_alignment", {
    steps: () => [
        {
            content: "Ensure we are in blog post page",
            trigger: ":iframe html[data-view-xmlid='website_blog.blog_post_complete']",
        },
        ...checkBlogElements("o_container_small"),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on main text block",
            trigger: ":iframe .website_blog section.s_text_block",
            run: "click",
        },
        {
            content: "Change container width to regular",
            trigger: "button[data-action-id='setContainerWidth'][data-action-param='container']",
            run: "click",
        },
        ...clickOnSave(),
        ...checkBlogElements("container"),
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on main text block",
            trigger: ":iframe .website_blog section.s_text_block",
            run: "click",
        },
        {
            content: "Change container width to full-width",
            trigger:
                "button[data-action-id='setContainerWidth'][data-action-param='container-fluid']",
            run: "click",
        },
        ...clickOnSave(),
        ...checkBlogElements("container-fluid"),
    ],
});
