odoo.define('test_website.image_upload_progress', function (require) {
'use strict';

const tour = require('web_tour.tour');

const { FileSelectorControlPanel } = require('@web_editor/components/media_dialog/file_selector');
const { patch, unpatch } = require('web.utils');

let patchWithError = false;
const patchMediaDialog = () => patch(FileSelectorControlPanel.prototype, 'test_website.mock_image_widgets', {
    async onChangeFileInput() {
        const getFileFromB64 = (fileData) => {
            const binary = atob(fileData[2]);
            let len = binary.length;
            const arr = new Uint8Array(len);
            while (len--) {
                arr[len] = binary.charCodeAt(len);
            }
            return new File([arr], fileData[1], {type: fileData[0]});
        };

        let files = [
            getFileFromB64(['image/vnd.microsoft.icon', 'icon.ico', "AAABAAEAAQEAAAEAIAAwAAAAFgAAACgAAAABAAAAAgAAAAEAIAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAA=="]),
            getFileFromB64(['image/webp', 'image.webp', "UklGRhwAAABXRUJQVlA4TBAAAAAvE8AEAAfQhuh//wMR0f8A"]),
            getFileFromB64(['image/png', 'image.png', "iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAApElEQVR42u3RAQ0AAAjDMO5fNCCDkC5z0HTVrisFCBABASIgQAQEiIAAAQJEQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAREQIAICBABASIgQAQECBAgAgJEQIAIyPcGFY7HnV2aPXoAAAAASUVORK5CYII="]),
            getFileFromB64(['image/jpeg', 'image.jpeg', "/9j/4AAQSkZJRgABAQAAAQABAAD//gAfQ29tcHJlc3NlZCBieSBqcGVnLXJlY29tcHJlc3P/2wCEAA0NDQ0ODQ4QEA4UFhMWFB4bGRkbHi0gIiAiIC1EKjIqKjIqRDxJOzc7STxsVUtLVWx9aWNpfZeHh5e+tb75+f8BDQ0NDQ4NDhAQDhQWExYUHhsZGRseLSAiICIgLUQqMioqMipEPEk7NztJPGxVS0tVbH1pY2l9l4eHl761vvn5///CABEIAEsASwMBIgACEQEDEQH/xAAVAAEBAAAAAAAAAAAAAAAAAAAABv/aAAgBAQAAAACHAAAAAAAAAAAAAAAAH//EABUBAQEAAAAAAAAAAAAAAAAAAAAH/9oACAECEAAAAKYAAAB//8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/2gAIAQMQAAAAngAAAf/EABQQAQAAAAAAAAAAAAAAAAAAAGD/2gAIAQEAAT8ASf/EABQRAQAAAAAAAAAAAAAAAAAAAED/2gAIAQIBAT8AT//EABQRAQAAAAAAAAAAAAAAAAAAAED/2gAIAQMBAT8AT//Z"]),
        ];

        if (!this.props.multiImages) {
            if (patchWithError) {
                files = [files[0]];
            } else {
                files = [files[2]];
            }
        }
        await this.props.uploadFiles(files);
    }
});

const unpatchMediaDialog = () => unpatch(FileSelectorControlPanel.prototype, 'test_website.mock_image_widgets');

const setupSteps = [{
    content: "reload to load patch",
    trigger: ".o_website_preview",
    run: () => {
        patchMediaDialog();
    },
}, {
    content: "enter edit mode",
    trigger: ".o_edit_website_container a"
}, {
    content: "drop a snippet",
    trigger: "#oe_snippets .oe_snippet[name='Text - Image'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
    extra_trigger: "body.editor_has_snippets",
    moveTrigger: "iframe .oe_drop_zone",
    run: "drag_and_drop iframe #wrap",
}, {
    content: "drop a snippet",
    trigger: "#oe_snippets .oe_snippet[name='Image Gallery'] .oe_snippet_thumbnail:not(.o_we_already_dragging)",
    extra_trigger: "body.editor_has_snippets",
    moveTrigger: ".oe_drop_zone",
    run: "drag_and_drop iframe #wrap",
}];

const formatErrorMsg = "format is not supported. Try with: .gif, .jpe, .jpeg, .jpg, .png, .svg";

tour.register('test_image_upload_progress', {
    url: `/web#action=website.website_preview&path=${encodeURI('/test_image_progress')}`,
    test: true
}, [
    ...setupSteps,
    // 1. Check multi image upload
    {
        content: "click on dropped snippet",
        trigger: "iframe #wrap .s_image_gallery .img",
    }, {
        content: "click on add images to open image dialog (in multi mode)",
        trigger: 'we-customizeblock-option [data-add-images]',
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        run: () => {
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            document.body.querySelector('.o_select_media_dialog .o_file_input').dispatchEvent(new Event('change'));
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
        trigger: "iframe #wrap .s_text_image .img",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        run: () => {
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            document.body.querySelector('.o_select_media_dialog .o_file_input').dispatchEvent(new Event('change'));
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
        trigger: "iframe #wrap .s_text_image .img",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        in_modal: false,
        run: () => {
            patchWithError = true;
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            document.body.querySelector('.o_select_media_dialog .o_file_input').dispatchEvent(new Event('change'));

        },
    }, {
        content: "check upload progress bar is correctly shown",
        trigger: `.o_we_progressbar:contains('icon.ico'):contains('${formatErrorMsg}')`,
        in_modal: false,
        run: function () {
            patchWithError = false;
        },
    }, {
        content: "there should only have one notification toaster",
        trigger: ".o_notification",
        in_modal: false,
        run: () => {
            const notificationCount = $('.o_notification').length;
            if (notificationCount !== 1) {
                console.error("There should be one noficiation toaster opened, and only one.");
            }
            unpatchMediaDialog();
        }
    },
]);


tour.register('test_image_upload_progress_unsplash', {
    url: `/web#action=website.website_preview&path=${encodeURI('/test_image_progress')}`,
    test: true
}, [
    ...setupSteps,
    // 1. Check multi image upload
    {
        content: "click on dropped snippet",
        trigger: "iframe #wrap .s_image_gallery .img",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
    }, {
        content: "search 'fox' images",
        trigger: ".o_we_search",
        run: "text fox",
    }, {
        content: "click on unsplash result", // note that unsplash is mocked
        trigger: "img[alt~=fox]"
    }, {
        content: "check that the upload progress bar is correctly shown",
        // ensure it is there so we are sure next step actually test something
        extra_trigger: '.o_notification_close',
        trigger: ".o_we_progressbar:contains('fox'):contains('File has been uploaded')",
        in_modal: false,
        run: function () {}, // it's a check
    }, {
        content: "notification should close after 3 seconds",
        trigger: 'body:not(:has(.o_notification_close))',
        in_modal: false,
    }, {
        content: "unsplash image (mocked to logo) should have been used",
        trigger: "iframe #wrap .s_image_gallery .img[data-original-src^='/unsplash/HQqIOc8oYro/fox']",
        run: () => {
            unpatchMediaDialog();
        },
    },
]);

});
