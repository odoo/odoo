import { registry } from "@web/core/registry";

registry
    .category("website.snippets")
    .category("category")
    .add("custom", {
        title: "Custom",
        image: "/website/static/src/img/snippets_thumbs/s_media_list.svg",
    })
    .add("intro", {
        title: "Intro",
        image: "/website/static/src/img/snippets_thumbs/s_cover.svg",
    })
    .add("columns", {
        title: "Columns",
        image: "/website/static/src/img/snippets_thumbs/s_three_columns.svg",
    })
    .add("content", {
        title: "Content",
        image: "/website/static/src/img/snippets_thumbs/s_text_image.svg",
    })
    .add("images", {
        title: "Images",
        image: "/website/static/src/img/snippets_thumbs/s_picture.svg",
    })
    .add("text", {
        title: "Text",
        image: "/website/static/src/img/snippets_thumbs/s_text_block.svg",
    })
    .add("contact_and_forms", {
        title: "Contact & Forms",
        image: "/website/static/src/img/snippets_thumbs/s_website_form.svg",
    })
    .add("social", {
        title: "Social",
        image: "/website/static/src/img/snippets_thumbs/s_instagram_page.svg",
    })
    .add("debug", {
        title: "Debug",
        image: "/website/static/src/img/snippets_thumbs/s_debug_group.png",
        isAvailable: (env) => {
            return !!env.debug;
        },
    })
    .add("products", {
        title: "Products",
        image: "/website/static/src/img/snippets_thumbs/s_dynamic_products.svg",
        install: "website_sale",
    })
    .add("blogs", {
        title: "Blogs",
        image: "/website/static/src/img/snippets_thumbs/s_blog_posts.svg",
        install: "website_blog",
    })
    .add("events", {
        title: "Events",
        image: "/website/static/src/img/snippets_thumbs/s_event_upcoming_snippet.svg",
        install: "website_event",
    });
