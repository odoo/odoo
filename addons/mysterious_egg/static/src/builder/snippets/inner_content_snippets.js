import { registry } from "@web/core/registry"

registry
    .category("website.snippets")
    .category("inner_content")
    .add("button", {
        title: "Button",
        image: "/website/static/src/img/snippets_thumbs/s_button.svg",
        templateContent: "website.s_button",
    })
    .add("image", {
        title: "Image",
        image: "/website/static/src/img/snippets_thumbs/s_image.svg",
        templateContent: "website.s_image",
    })
    .add("video", {
        title: "Video",
        image: "/website/static/src/img/snippets_thumbs/s_video.svg",
        templateContent: "website.s_video",
    })
    .add("separator", {
        title: "Separator",
        image: "/website/static/src/img/snippets_thumbs/s_hr.svg",
        templateContent: "website.s_hr",
    })
    .add("accordion", {
        title: "Accordion",
        image: "/website/static/src/img/snippets_thumbs/s_accordion.svg",
        templateContent: "website.s_accordion",
    })
    .add("alert", {
        title: "Alert",
        image: "/website/static/src/img/snippets_thumbs/s_alert.svg",
        templateContent: "website.s_alert",
    })
    .add("rating", {
        title: "Rating",
        image: "/website/static/src/img/snippets_thumbs/s_rating.svg",
        templateContent: "website.s_rating",
    })
    .add("card", {
        title: "Card",
        image: "/website/static/src/img/snippets_thumbs/s_card.svg",
        templateContent: "website.s_card",
    })
    .add("share", {
        title: "Share",
        image: "/website/static/src/img/snippets_thumbs/s_share.svg",
        templateContent: "website.s_share",
    })
    .add("social_media", {
        title: "Social Media",
        image: "/website/static/src/img/snippets_thumbs/s_social_media.svg",
        templateContent: "website.s_social_media",
    })
    .add("facebook", {
        title: "Facebook",
        image: "/website/static/src/img/snippets_thumbs/s_facebook_page.svg",
        templateContent: "website.s_facebook_page",
    })
    .add("search", {
        title: "Search",
        image: "/website/static/src/img/snippets_thumbs/s_searchbar_inline.svg",
        templateContent: "website.s_searchbar_input",
        //TODO t-forbid-sanitize="form"
    })
    .add("text_highlight", {
        title: "Text Highlight",
        image: "/website/static/src/img/snippets_thumbs/s_text_highlight.svg",
        templateContent: "website.s_text_highlight",
    })
    .add("chart", {
        title: "Chart",
        image: "/website/static/src/img/snippets_thumbs/s_chart.svg",
        templateContent: "website.s_chart",
    })
    .add("progress_bar", {
        title: "Progress Bar",
        image: "/website/static/src/img/snippets_thumbs/s_progress_bar.svg",
        templateContent: "website.s_progress_bar",
    })
    .add("badge", {
        title: "Badge",
        image: "/website/static/src/img/snippets_thumbs/s_badge.svg",
        templateContent: "website.s_badge",
    })
    .add("cta_badge", {
        title: "CTA Badge",
        image: "/website/static/src/img/snippets_thumbs/s_cta_badge.svg",
        templateContent: "website.s_cta_badge",
    })
    .add("blockquote", {
        title: "Blockquote",
        image: "/website/static/src/img/snippets_thumbs/s_blockquote.svg",
        templateContent: "website.s_blockquote",
    })
    .add("form", {
        title: "Form",
        image: "/website/static/src/img/snippets_thumbs/s_website_form.svg",
        templateContent: "website.s_website_form",
        // TODO t-forbid-sanitize="form"
    })
    .add("countdown", {
        title: "Countdown",
        image: "/website/static/src/img/snippets_thumbs/s_countdown.svg",
        templateContent: "website.s_countdown",
    })
    .add("embed_code", {
        title: "Embed Code",
        image: "/website/static/src/img/snippets_thumbs/s_embed_code.svg",
        templateContent: "website.s_embed_code",
        // TODO t-forbid-sanitize="true"
    })
    .add("map", {
        title: "Map",
        image: "/website/static/src/img/snippets_thumbs/s_map.svg",
        templateContent: "website.s_map",
        isAvailable: (env) => {
            return !!env.debug // TODO "or not google_maps_api_key"
        }
    })
    .add("google_map", {
        title: "Map",
        image: "/website/static/src/img/snippets_thumbs/s_google_map.svg",
        templateContent: "website.s_google_map",
        isAvailable: (env) => {
            return !!env.debug // TODO "or google_maps_api_key"
        }
    })
