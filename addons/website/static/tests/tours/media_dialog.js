import {
    clickOnSave,
    insertSnippet,
    registerWebsitePreviewTour,
    openPowerbox,
} from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "website_media_dialog_undraw",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            content: "Open the media dialog from the snippet",
            trigger: ":iframe .s_text_image img",
            run: "dblclick",
        },
        {
            content: "Search for 'banner' to call the media library", // Mocked call
            trigger: ".o_select_media_dialog .o_we_search",
            run: "edit banner",
        },
        {
            content: "Check that the media library is available",
            trigger:
                '.o_select_media_dialog:has(.o_we_search_select option[value="media-library"])',
        },
        {
            content:
                "Ensure all images are loaded to avoid CORS is misconfigured on the API server, image will be treated as non-dynamic.",
            trigger: ".modal .o_load_done_msg",
        },
    ]
);

registerWebsitePreviewTour(
    "website_media_dialog_external_library",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            content: "Open the media dialog from the snippet",
            trigger: ":iframe .s_text_image img",
            run: "dblclick",
        },
        {
            content: "Dummy search to call the media library",
            trigger: ".o_select_media_dialog .o_we_search",
            run: "edit a",
        },
        {
            content: "Choose the media library to only show its media",
            trigger: ".o_select_media_dialog .o_we_search_select",
            run: "select Illustrations",
        },
        {
            content: "Double click on the first image",
            trigger: ".o_select_media_dialog img.o_we_attachment_highlight",
            run: "click",
        },
        {
            content: "Reopen the media dialog",
            trigger: ":iframe .s_text_image img",
            run: "dblclick",
        },
        {
            content: "Check that the image was created only once",
            trigger:
                ".o_select_media_dialog .o_we_existing_attachments .o_existing_attachment_cell img[src^='/html_editor/shape/illustration/']",
            run() {
                const listEl = this.anchor.closest(
                    ".o_select_media_dialog .o_we_existing_attachments"
                );
                const selector =
                    ".o_existing_attachment_cell img[src^='/html_editor/shape/illustration/']";
                const uploadedImgs = listEl.querySelectorAll(
                    `${selector}[title='${this.anchor.title}']`
                );
                if (uploadedImgs.length !== 1) {
                    throw new Error(
                        `${uploadedImgs.length} attachment(s) were found. Exactly 1 should have been created.`
                    );
                }
            },
        },
        {
            content: "Click on the first illustration image",
            trigger: ".o_select_media_dialog .o_we_attachment_highlight",
            run: "click",
        },
        {
            content: "Select the image",
            trigger: ":iframe .s_text_image img",
            run: "click",
        },
        {
            content: "Try to crop the image",
            trigger: "#oe_snippets .o_we_customize_panel .o_we_user_value_widget[data-crop='true']",
            run: "click",
        },
        {
            content: "Observe the crop is denied for illustration image",
            trigger: ".o_notification_manager .o_notification",
        },
        ...clickOnSave(),
    ]
);

registerWebsitePreviewTour(
    "website_media_dialog_icons",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_social_media",
            name: "Social Media",
        }),
        {
            content: "Open the icon picker from a snippet icon",
            trigger: ":iframe .s_social_media [data-icon='oi_instagram']",
            run: "dblclick",
        },
        {
            content: "Check that every listed icon renders correctly",
            trigger: ".o-IconPicker .o-IconPicker-icon",
            async run() {
                await document.fonts.ready;
                // A glyph is as wide as the font size, whereas an icon missing
                // from the font shows its name instead.
                const failures = [
                    ...this.anchor.closest(".o-IconPicker").querySelectorAll(".o-IconPicker-icon"),
                ]
                    .filter((iconEl) => {
                        const width = parseFloat(getComputedStyle(iconEl, "::before").width);
                        return Math.abs(width - parseFloat(getComputedStyle(iconEl).fontSize)) > 1;
                    })
                    .map((iconEl) => iconEl.dataset.icon);

                if (failures.length) {
                    throw new Error(`Icons not correctly rendered: ${failures.join(", ")}`);
                }
            },
        },
        {
            content: "Pick the same icon",
            trigger: ".o-IconPicker .o-IconPicker-icon.o-selected[data-icon='oi_instagram']",
            run: "click",
        },
        {
            content: "Check if the icon remains the same",
            trigger: ":iframe .s_social_media [data-icon='oi_instagram']",
        },
        {
            content: "Open the icon picker again",
            trigger: ":iframe .s_social_media [data-icon='oi_instagram']",
            run: "dblclick",
        },
        {
            content: "Close it without picking an icon",
            trigger: ".o-IconPicker input[role=combobox]",
            run: "press Escape",
        },
        {
            content: "Check if the icon remains the same",
            trigger: ":iframe .s_social_media [data-icon='oi_instagram']",
        },
        ...clickOnSave(),
    ]
);

registerWebsitePreviewTour(
    "website_media_dialog_insert_media",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        {
            content: "Click on the first paragraph",
            trigger: ":iframe .s_text_block p",
            run: "editor test",
        },
        openPowerbox(":iframe .s_text_block p:last-child"),
        {
            content: "Click on the icon item from powerbox",
            trigger: "div.o-we-command-name:contains('Icon')",
            run: "click",
        },
        {
            content: "Click on the first icon",
            trigger: ".o-IconPicker .o-IconPicker-icon",
            run: "click",
        },
        {
            content: "Verify that the icon was inserted",
            trigger: ":iframe .s_text_block p > span.oi",
        },
    ]
);

registerWebsitePreviewTour(
    "website_media_dialog_insert_file",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_block",
            name: "Text",
            groupName: "Text",
        }),
        {
            content: "Click on the first paragraph",
            trigger: ":iframe .s_text_block p",
            run: "editor test",
        },
        {
            content: "Show the powerbox",
            trigger: ":iframe .s_text_block p:last-child",
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
            content: "Click on the first document",
            trigger: ".o_select_media_dialog .o_existing_attachment_cell .o_button_area",
            run: "click",
        },
        {
            content:
                "Verify that the document was inserted and reopen the media dialog with a double click",
            trigger: ":iframe .s_text_block p > .o_file_box",
            run: "dblclick",
        },
        {
            content: "Verify that the dialog opened on the Documents tab",
            trigger: ".o_select_media_dialog button.nav-link.active:contains('Documents')",
        },
    ]
);

registerWebsitePreviewTour(
    "website_replace_remove_image",
    {
        edition: true,
    },
    () => [
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        {
            content: "Open the media dialog from the snippet",
            trigger: ":iframe .s_text_image img",
            run: "dblclick",
        },
        {
            content: "Click on the toolbar's 'Add URL' button",
            trigger: ".o_upload_media_url_button",
            run: "click",
        },
        {
            content: "Edit input field value",
            trigger: ".o_we_url_input",
            run: "edit website/static/src/img/backgrounds/city.jpg",
        },
        {
            content: "Click on the toolbar's 'Add URL' button",
            trigger: ".o_upload_media_url_button",
            run: "click",
        },
        {
            content: "Open the media dialog from the snippet",
            trigger: ":iframe .s_text_image img",
            run: "dblclick",
        },
        {
            content: "Click on remove attachment",
            trigger: ".o_we_attachment_selected [data-icon='delete'].oi-filled:not(:visible)",
            run: "click",
        },
        {
            content: "Confirm the removal of the attachment",
            trigger: ".btn:contains('Delete')",
            run: "click",
        },
        {
            content: "Click 'Discard' to close the media dialog",
            trigger: ".modal:not(.o_inactive_modal) .o_select_media_dialog .btn:contains(Discard)",
            run: "click",
        },
        ...clickOnSave(),
        {
            content: "Ensure the image is replaced with a placeholder thumbnail",
            trigger:
                ":iframe .s_text_image img[src='/html_editor/static/src/img/placeholder_thumbnail.png']",
        },
    ]
);
