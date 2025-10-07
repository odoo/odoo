import {
    changeOption,
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "translate_website_media",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({ id: "s_picture", name: "Title - Image", groupName: "Images" }),
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
                ":iframe .s_picture img.o_savable_attribute[src='/web/image/website.landscape_md_2']",
            run: "click",
        },
        // Open the media dialog on Images
        changeOption("Image", "translateMediaSrc"),
        {
            content: "Select another image",
            trigger: "[aria-label='test.png']",
            run: "click",
        },
        {
            content: "Check: image has been modified",
            trigger:
                ":iframe .s_picture img.o_savable_attribute:not([src='/web/image/website.landscape_md_2'])",
        },
        {
            content: "Check: image is marked as translated",
            trigger: ":iframe .s_picture img.o_savable_attribute.o_modified_image_to_save",
        },
        // Document translation
        {
            content: "Click on file",
            trigger: ":iframe .o_file_box",
            run: "click",
        },
        // Open the media dialog on Documents
        changeOption("Block", "translateMediaSrc"),
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
            trigger: ":iframe .s_picture img:not([src='/web/image/website.landscape_md_2'])",
        },
        {
            content: "Check: document has been replaced",
            trigger: ":iframe .o_file_box .o_file_image[title='file_translated.txt']",
        },
        {
            content: "return to english version",
            trigger: ':iframe .js_language_selector a[data-url_code="en"]',
            run: "click",
        },
        // Original media checks
        {
            content: "Check: original image is still there",
            trigger: ":iframe .s_picture img[src='/web/image/website.landscape_md_2']",
        },
        {
            content: "Check: original document is still there",
            trigger: ":iframe .o_file_box .o_file_image[title='file.txt']",
        },
    ]
);
