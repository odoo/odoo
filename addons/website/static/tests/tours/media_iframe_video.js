import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour("website_media_iframe_video", {
        url: "/",
        edition: true,
    }, () => [
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            content: "Select the image",
            trigger: ":iframe #wrap .s_text_image img",
            run: "click",
        },
        {
            content: "Open image link options",
            trigger: "[data-name='media_link_opt']",
            run: "click",
        },
        {
            content: "Enter the url",
            trigger: "input[placeholder='www.example.com']",
            run: "edit odoo.com",
        },
        {
            content: "Click on replace media",
            trigger: "[data-replace-media='true']",
            run: "click",
        },
        {
            content: "Click on video button",
            trigger: "a:contains('Videos')",
            run: "click",
        },
        {
            content: "Enter text in video link input to enable add button",
            trigger: "#o_video_text",
            run: "edit https://youtu.be/nbso3NVz3p8",
        },
        {
            content: "Wait for add button to be enabled",
            trigger: ".modal-footer button:contains('Add'):not([disabled])",
            run: () => {},
        },
        {
            content: "Remove video link",
            trigger: "#o_video_text",
            run() {
                const inputEl = this.anchor;
                inputEl.value = "";
                inputEl.dispatchEvent(new Event("input", { bubbles: true }));
            },
        },
        {
            content: "Video input field should not be in valid state",
            trigger: "#o_video_text:not(.is-valid)",
            run: () => {},
        },
        {
            content: "Check that the preview is not shown",
            trigger: ".media_iframe_video:not(:has(iframe))",
            run: () => {},
        },
        {
            content: "Check that the add button is disabled in footer",
            trigger: ".modal-footer",
            run: function () {
                const addButtonEl = this.anchor.querySelector(".btn.btn-primary");
                if (!addButtonEl.disabled) {
                    console.error("Add button is not disabled.");
                }
            },
        },
        {
            content: "Enter video link",
            trigger: "#o_video_text",
            run: "edit https://youtu.be/nbso3NVz3p8",
        },
        {
            content: "Check video is preview",
            trigger: ".o_video_dialog_iframe",
        },
        {
            content: "Click on 'add' button",
            trigger: ".modal-footer button:contains('Add')",
            run: "click",
        },
        {
            content: "Ensure that the parent of media_iframe_video is not an 'a' tag.",
            trigger: ":iframe .media_iframe_video",
            run: function () {
                if (this.anchor.parentElement.tagName === "A") {
                    console.error("Iframe video has link!!!");
                }
            },
        },
    ]
);

registerWebsitePreviewTour(
    "website_media_iframe_video_options",
    {
        url: "/",
        edition: true,
    }, () => [
        ...insertSnippet({
            id: 's_video',
            name: 'Video',
        }),
        {
            content: "Select the Video",
            trigger: ":iframe #footer .media_iframe_video",
            run: "click",
        },
        {
            content: "Click on replace media",
            trigger: "[data-replace-media='true']",
            run: "click",
        },
        {
            content: "Enter video link",
            trigger: "#o_video_text",
            run: "edit https://youtu.be/nbso3NVz3p8",
        },
        {
            content: "Check for preview to appear",
            trigger: ".o_video_dialog_iframe",
            run: () => {}, // This is a check.
        },
        {
            content: "Toggle ON autoplay button",
            trigger: ".o_video_dialog_options label:contains('Autoplay') .o_switch",
            run: "click",
        },
        {
            content: "Check '&autoplay=1' is present in URL",
            trigger: ".o_video_dialog_form textarea",
            async run() {
                // Let the previous step performed. 
                await new Promise(resolve => setTimeout(resolve, 1000));
                if (!this.anchor.value.includes("&autoplay=1")) {
                    throw new Error("After enabling autoplay, URL should include '&autoplay=1'");
                }
            }
        },
        {
            content: "Add '&loop=1' in the video URL",
            trigger: ".o_video_dialog_form",
            run() {
                const textarea = this.anchor.querySelector("#o_video_text");
                textarea.value = textarea.value + "&loop=1";
                textarea.dispatchEvent(new Event("input"));
            },
        },
        {
            content: "Verify Loop option toggles ON automatically",
            trigger: ".o_video_dialog_options label:contains('Loop') .o_switch",
            async run() {
                // Let the previous step performed. 
                await new Promise(resolve => setTimeout(resolve, 1000));
                if (!this.anchor.querySelector("input").checked) {
                    throw new Error("After adding '&loop=1' in URL, Loop option should toggle ON");
                }
            },
        },
        {
            content: "Click on 'add' button",
            trigger: ".modal-footer button:contains('Add')",
            run: "click",
        },
        {
            content: "Ensure iframe has video src according to enabled options",
            trigger: ":iframe .media_iframe_video",
            run() {
                const src = this.anchor.querySelector("iframe").src;
                if (!src.includes("$autoplay=1") && !src.includes("&loop=1")) {
                    throw new Error("Iframe should include '&autoplay=1' and '&loop=1'.");
                }
            },
        },
    ]
);

