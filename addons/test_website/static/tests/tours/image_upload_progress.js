odoo.define('test_website.image_upload_progress', function (require) {
'use strict';

const tour = require('web_tour.tour');

const formatErrorMsg = "format is not supported. Try with: .gif, .jpe, .jpeg, .jpg, .png, .svg";

tour.register('test_image_upload_progress', {
    url: '/test_image_progress',
    test: true
}, [
    {
        content: "enter edit mode",
        trigger: "a[data-action=edit]"
    }, {
        content: "drop a snippet",
        trigger: "#oe_snippets .oe_snippet[name='Text - Image'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        extra_trigger: "body.editor_enable.editor_has_snippets",
        moveTrigger: ".oe_drop_zone",
        run: "drag_and_drop #wrap",
    }, {
        content: "drop a snippet",
        trigger: "#oe_snippets .oe_snippet[name='Image Gallery'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
        extra_trigger: "body.editor_enable.editor_has_snippets",
        moveTrigger: ".oe_drop_zone",
        run: "drag_and_drop #wrap",
    },
    // 1. Check multi image upload
    {
        content: "click on dropped snippet",
        trigger: "#wrap .s_image_gallery .img",
    }, {
        content: "click on add images to open image dialog (in multi mode)",
        trigger: 'we-customizeblock-option [data-add-images]',
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        run: () => {
            const fileInput = $('.o_select_media_dialog .o_file_input').first();
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            // See `mock_image_widgets`.
            fileInput.change();
        },
    }, {
        content: "check upload progress bar is correctly shown (1)",
        trigger: `.o_we_progressbar:contains('icon.ico'):contains('${formatErrorMsg}')`,
        in_modal: false,
        run: function () {}, // it's a check
    }, {
        content: "check upload progress bar is correctly shown (2)",
        trigger: `.o_we_progressbar:contains('image.webp'):contains('${formatErrorMsg}')`,
        in_modal: false,
        run: function () {}, // it's a check
    }, {
        content: "check upload progress bar is correctly shown (3)",
        trigger: ".o_we_progressbar:contains('image.png'):contains('File has been uploaded')",
        in_modal: false,
        run: function () {}, // it's a check
    }, {
        content: "check upload progress bar is correctly shown (4)",
        trigger: ".o_we_progressbar:contains('image.jpeg'):contains('File has been uploaded')",
        in_modal: false,
        run: function () {}, // it's a check
    }, {
        content: "there should only have one notification toaster",
        trigger: ".o_notification",
        in_modal: false,
        run: () => {
            const notificationCount = $('.o_notification').length;
            if (notificationCount !== 1) {
                console.error("There should be one noficiation toaster opened, and only one.");
            }
        }
    }, {
        content: "close notification",
        trigger: '.o_notification_close',
        in_modal: false,
    }, {
        content: "close media dialog",
        trigger: '.modal-footer .btn-secondary',
    },
    // 2. Check success single image upload
    {
        content: "click on dropped snippet",
        trigger: "#wrap .s_text_image .img",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        in_modal: false,
        run: () => {
            const fileInput = $('.o_select_media_dialog .o_file_input').first();
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            // See `mock_image_widgets`.
            fileInput.change();
        },
    }, {
        content: "check upload progress bar is correctly shown",
        trigger: ".o_we_progressbar:contains('image.png'):contains('File has been uploaded')",
        in_modal: false,
        run: function () {}, // it's a check
    }, {
        content: "there should only have one notification toaster",
        trigger: ".o_notification",
        in_modal: false,
        run: () => {
            const notificationCount = $('.o_notification').length;
            if (notificationCount !== 1) {
                console.error("There should be one noficiation toaster opened, and only one.");
            }
        }
    }, {
        content: "close media dialog",
        trigger: 'button.btn.btn-secondary[type="button"]',
    }, {
        content: "toaster should disappear after a few seconds if the uploaded image is successful",
        trigger: "body:not(:has(.o_we_progressbar))",
        run: function () {}, // it's a check
    },
    // 3. Check error single image upload
    {
        content: "click on dropped snippet",
        trigger: "#wrap .s_text_image .img",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        in_modal: false,
        run: () => {
            $("#wrap .s_text_image .img").addClass('o_mock_show_error');
            const fileInput = $('.o_select_media_dialog .o_file_input').first();
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            // See `mock_image_widgets`.
            fileInput.change();
        },
    }, {
        content: "check upload progress bar is correctly shown",
        trigger: `.o_we_progressbar:contains('icon.ico'):contains('${formatErrorMsg}')`,
        in_modal: false,
        run: function () {}, // it's a check
    }, {
        content: "there should only have one notification toaster",
        trigger: ".o_notification",
        in_modal: false,
        run: () => {
            const notificationCount = $('.o_notification').length;
            if (notificationCount !== 1) {
                console.error("There should be one noficiation toaster opened, and only one.");
            }
        }
    },
]);

});
