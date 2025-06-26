/** @odoo-module **/

import { insertSnippet, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

import { FileSelectorControlPanel } from "@web_editor/components/media_dialog/file_selector";
import { patch } from "@web/core/utils/patch";

let patchWithError = false;
const patchMediaDialog = () => patch(FileSelectorControlPanel.prototype, {
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

        if (!this.props.multiSelect) {
            if (patchWithError) {
                files = [files[0]];
            } else {
                files = [files[2]];
            }
        }
        await this.props.uploadFiles(files);
    }
});

let unpatchMediaDialog = null;

const setupSteps = function () {
    return [
        {
            content: "reload to load patch",
            trigger: ".o_website_preview",
            run() {
                unpatchMediaDialog = patchMediaDialog();
            },
        },
        ...insertSnippet({
            id: "s_text_image",
            name: "Text - Image",
            groupName: "Content",
        }),
        ...insertSnippet({
            id: "s_image_gallery",
            name: "Image Gallery",
            groupName: "Images",
        })
    ];
};

const formatErrorMsg = "format is not supported. Try with: .gif, .jpe, .jpeg, .jpg, .png, .svg, .webp";

registerWebsitePreviewTour('test_image_upload_progress', {
    url: '/test_image_progress',
    edition: true,
}, () => [
    ...setupSteps(),
    // 1. Check multi image upload
    {
        content: "click on dropped snippet",
        trigger: ":iframe #wrap .s_image_gallery .img",
        run: "click",
    }, {
        content: "click on add images to open image dialog (in multi mode)",
        trigger: 'we-customizeblock-option [data-add-images]',
        run: "click",
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        run() {
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            document.body.querySelector('.o_select_media_dialog .o_file_input').dispatchEvent(new Event('change'));
        },
    }, {
        content: "check upload progress bar is correctly shown (1)",
        trigger: `.o_we_progressbar:contains('icon.ico'):contains('${formatErrorMsg}')`,
    }, {
        content: "check upload progress bar is correctly shown (2)",
        trigger: ".o_we_progressbar:contains('image.webp'):contains('File has been uploaded')",
    }, {
        content: "check upload progress bar is correctly shown (3)",
        trigger: ".o_we_progressbar:contains('image.png'):contains('File has been uploaded')",
    }, {
        content: "check upload progress bar is correctly shown (4)",
        trigger: ".o_we_progressbar:contains('image.jpeg'):contains('File has been uploaded')",
    },
    {
        trigger: ".o_notification",
    },
    {
        content: "there should only have one notification toaster",
        trigger: "body",
        run() {
            const notificationCount = document.querySelectorAll(".o_notification").length;
            if (notificationCount !== 1) {
                throw new Error(`There should be one notification toaster opened, and only one, found ${notificationCount}.`);
            }
        }
    }, {
        content: "close notification",
        trigger: '.o_notification_close',
        run: "click",
    }, {
        content: "close media dialog",
        trigger: '.modal-footer .btn-secondary',
        run: "click",
    },
    // 2. Check success single image upload
    {
        content: "click on dropped snippet",
        trigger: ":iframe #wrap .s_text_image .img",
        run: "click",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
        run: "click",
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        run() {
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            document.body.querySelector('.o_select_media_dialog .o_file_input').dispatchEvent(new Event('change'));
        },
    }, {
        content: "check upload progress bar is correctly shown",
        trigger: ".o_we_progressbar:contains('image.png')",
    }, {
        content: "there should only have one notification toaster",
        trigger: ".o_notification",
        run() {
            const notificationCount = document.querySelectorAll(".o_notification").length;
            if (notificationCount !== 1) {
                throw new Error(`There should be one notification toaster opened, and only one, found ${notificationCount}.`);
            }
        }
    }, {
        content: "media dialog has closed after the upload",
        trigger: 'body:not(:has(.o_select_media_dialog))',
    }, {
        content: "the upload progress toast was updated",
        trigger: ".o_we_progressbar:contains('image.png'):contains('File has been uploaded')",
    }, {
        content: "toaster should disappear after a few seconds if the uploaded image is successful",
        trigger: "body:not(:has(.o_we_progressbar))",
    },
    // 3. Check error single image upload
    {
        content: "click on dropped snippet",
        trigger: ":iframe #wrap .s_text_image .img",
        run: "click",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
        run: "click",
    }, {
        content: "manually trigger input change",
        trigger: ".o_select_media_dialog .o_upload_media_button",
        run() {
            patchWithError = true;
            // This will trigger upload of dummy files for test purpose, as a
            // test can't select local files to upload into the input.
            document.body.querySelector('.o_select_media_dialog .o_file_input').dispatchEvent(new Event('change'));

        },
    }, {
        content: "check upload progress bar is correctly shown",
        trigger: `.o_we_progressbar:contains('icon.ico'):contains('${formatErrorMsg}')`,
        run() {
            patchWithError = false;
        },
    }, {
        content: "there should only have one notification toaster",
        trigger: ".o_notification",
        run() {
            const notificationCount = document.querySelectorAll(".o_notification").length;
            if (notificationCount !== 1) {
                throw new Error(`There should be one noficiation toaster opened, and only one, found ${notificationCount}.`);
            }
            unpatchMediaDialog();
        }
    },
]);


registerWebsitePreviewTour('test_image_upload_progress_unsplash', {
    url: '/test_image_progress',
    edition: true,
}, () => [
    ...setupSteps(),
    // 1. Check multi image upload
    {
        content: "click on dropped snippet",
        trigger: ":iframe #wrap .s_image_gallery .img",
        run: "click",
    }, {
        content: "click on replace media to open image dialog",
        trigger: 'we-customizeblock-option [data-replace-media]',
        run: "click",
    }, {
        content: "search 'fox' images",
        trigger: ".o_we_search",
        run: "edit fox",
    }, {
        content: "click on unsplash result", // note that unsplash is mocked
        trigger: "img[alt~=fox]",
        run: "click",
    },
    {
        trigger: ".o_notification_close",
    },
    {
        content: "check that the upload progress bar is correctly shown",
        // ensure it is there so we are sure next step actually test something
        trigger: ".o_we_progressbar:contains('fox'):contains('File has been uploaded')",
    }, {
        content: "notification should close after 3 seconds",
        trigger: 'body:not(:has(.o_notification_close))',
        run: "click",
    }, {
        content: "unsplash image (mocked to logo) should have been used",
        trigger: ":iframe #wrap .s_image_gallery .img[data-original-src^='/unsplash/HQqIOc8oYro/fox']",
        run() {
            unpatchMediaDialog();
        },
    },
]);
