import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "translate_website_media",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_picture", name: "Title - Image", groupName: "Images" }),
        ...insertSnippet({ id: "s_video", name: "Video" }, { ignoreLoading: true }),
        {
            content: "Add a video URL",
            trigger: ".o_select_media_dialog #o_video_text",
            run: `edit https://www.youtube.com/watch?v=G8b4UZIcTfg`,
        },
        {
            content: "Add the video",
            trigger: ".o_select_media_dialog .modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Show the powerbox",
            trigger: ":iframe .s_picture p",
            async run(actions) {
                await actions.editor(`/`);
                const wrapwrap = this.anchor.closest("#wrapwrap");
                wrapwrap.dispatchEvent(
                    new InputEvent("input", {
                        inputType: "insertText",
                        data: "/",
                    })
                );
            },
        },
        {
            content: "Click on the media item from powerbox",
            trigger: "div.o-we-command-name:contains('Media')",
            run: "click",
        },
        {
            content: "Click on the 'Documents' tab",
            trigger: ".o_select_media_dialog button.nav-link:contains('Documents')",
            run: "click",
        },
        {
            content: "Select a file",
            trigger: ".o_select_media_dialog .o_button_area[aria-label='file.txt']",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Change the language to French",
            trigger: ':iframe .js_language_selector .js_change_lang[data-url_code="fr"]',
            run: "click",
        },
        {
            content: "Click edit button",
            trigger: ".o_menu_systray button:contains('Edit').dropdown-toggle",
            run: "click",
        },
        {
            content: "Enable translation",
            trigger: ".o_translate_website_dropdown_item",
            run: "click",
        },
        {
            content: "Close the dialog",
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        // Image translation
        {
            content: "Click on image",
            trigger:
                ":iframe .s_picture img.o_savable_attribute[src='/web/image/website.s_picture_default_image']",
            run: "click",
        },
        {
            content: "Open the media dialog",
            trigger:
                ".options-container [data-action-id='translateMediaSrc'][data-action-param='images']",
            run: "click",
        },
        {
            content: "Select another image",
            trigger: "[aria-label='one_pixel.png']",
            run: "click",
        },
        {
            content: "Check: image has been modified",
            trigger:
                ":iframe .s_picture img.o_savable_attribute:not([src='/web/image/website.s_picture_default_image'])",
        },
        {
            content: "Check: image is marked as translated",
            trigger: ":iframe .s_picture img.o_savable_attribute.o_modified_image_to_save",
        },
        // Video translation
        {
            content: "Click on video",
            trigger: ":iframe .media_iframe_video.o_savable_attribute",
            run: "click",
        },
        {
            content: "Open the media dialog",
            trigger:
                ".options-container [data-action-id='translateMediaSrc'][data-action-param='videos']",
            run: "click",
        },
        {
            content: "Select another video",
            trigger: ".o_select_media_dialog #o_video_text",
            run: "edit https://www.youtube.com/watch?v=qxb74CMR748",
        },
        {
            content: "Check that the preview was updated",
            trigger: ".o_select_media_dialog .o_video_dialog_iframe[src*='qxb74CMR748']",
        },
        {
            content: "Add the video",
            trigger: ".o_select_media_dialog .modal-footer .btn-primary",
            run: "click",
        },
        // Document translation
        {
            content: "Click on file",
            trigger: ":iframe .o_file_box",
            run: "click",
        },
        {
            content: "Open the media dialog",
            trigger:
                ".options-container [data-action-id='translateMediaSrc'][data-action-param='documents']",
            run: "click",
        },
        {
            content: "Select another file",
            trigger: ".o_select_media_dialog .o_button_area[aria-label='file_translated.txt']",
            run: "click",
        },
        {
            content: "Check: the file box DOM is marked as dirty",
            trigger: ":iframe span.o_savable.o_dirty .o_file_box",
        },
        ...clickOnSave(),
        // Translations checks
        {
            content: "Check: image has been replaced",
            trigger:
                ":iframe .s_picture img:not([src='/web/image/website.s_picture_default_image'])",
        },
        {
            content: "Check: video has been replaced",
            trigger: ":iframe .media_iframe_video[data-oe-expression*='qxb74CMR748']",
        },
        {
            content: "Check: document has been replaced",
            trigger: ":iframe .o_file_box .o_file_image[title='file_translated.txt']",
        },
        {
            content: "open language selector",
            trigger: ":iframe .js_language_selector button:first",
            run: "click",
        },
        {
            content: "return to english version",
            trigger: ':iframe .js_language_selector a[data-url_code="en"]',
            run: "click",
        },
        // Original media checks
        {
            content: "Check: original image is still there",
            trigger: ":iframe .s_picture img[src='/web/image/website.s_picture_default_image']",
        },
        {
            content: "Check: original video is still there",
            trigger: ":iframe .media_iframe_video[data-oe-expression*='G8b4UZIcTfg']",
        },
        {
            content: "Check: original document is still there",
            trigger: ":iframe .o_file_box .o_file_image[title='file.txt']",
        },
    ]
);
