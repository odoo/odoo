/** @odoo-module */

import tour from "web_tour.tour";
import wTourUtils from "website.tour_utils";

tour.register(
    "website_media_iframe_video", {
        test: true,
        url: "/",
}, [
        {
            trigger: "a[data-action=edit]",
        },
        wTourUtils.dragNDrop({
            id: "s_text_image",
            name: "Text - Image",
        }),
        {
            content: "Select the image",
            trigger: "#wrap .s_text_image img",
            run: "click"
        },
        {
            content: "Open image link options",
            trigger: "[data-name='media_link_opt']",
            run: "click"
        },
        {
            content: "Enter the url",
            trigger: "input[placeholder='www.example.com']",
            run: "text odoo.com"
        },
        {
            content: "Click on replace media",
            trigger: "[data-replace-media='true']",
            run: "click"
        },
        {
            content: "Click on video button",
            trigger: "a[aria-controls='editor-media-video']",
            run: "click"
        },
        {
            content: "Enter video link",
            trigger: "#o_video_text",
            run: "text https://youtu.be/nbso3NVz3p8"
        },
        {
            content: "Click on 'add' button",
            trigger: ".modal-footer button:contains('Add')",
            run: "click"
        },
        {
            content: "Check media_iframe_video parent has an 'a' tag",
            trigger: "body",
            run: () => {
                if(document.querySelector(".media_iframe_video").parentElement.tagName === "A") {
                    console.error("Iframe video has link!!!")
                }
            }
        },
    ]
);
