/** @odoo-module */

import wTourUtils from '@website/js/tours/tour_utils';

export const mockCanvasToDataURLStep = {
    content: "Setup mock HTMLCanvasElement.toDataURL",
    trigger: "body",
    run() {
        const _super = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function (type, quality) {
            return _super.call(this, type === "image/webp" ? "image/png" : type, quality);
        };
    },
};

export function uploadImageFromDialog(
    mimetype,
    filename,
    data,
    confirmChoice = true,
    targetSelector = ".o_we_existing_attachments .o_we_attachment_selected img",
) {
    return [
        {
            content: "Upload an image",
            trigger: '.o_upload_media_button',
            async run() {
                const imageData = Uint8Array.from([...atob(data)].map((c) => c.charCodeAt(0)));
                const fileInput = document.querySelector('.o_select_media_dialog input[type="file"]');
                let file = new File([imageData], filename, { type: mimetype });
                let transfer = new DataTransfer();
                transfer.items.add(file);
                fileInput.files = transfer.files;
                fileInput.dispatchEvent(new Event("change"));
            },
        },
        ...wTourUtils.waitForImageToLoad(targetSelector),
        ...(confirmChoice ? [{
            content: "Confirm choice",
            trigger: '.o_select_media_dialog footer button:contains("Add")',
            extraTrigger: ".o_we_existing_attachments .o_we_attachment_selected",
        }] : []),
    ];
}

export const PNG_THAT_CONVERTS_TO_BIGGER_WEBP = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQIW2NgAAIAAAUAAR4f7BQAAAAASUVORK5CYII=";

export function generateTestPng(size) {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    return canvas.toDataURL("image/png");
}

const selectImage = {
    content: "Select image",
    trigger: "iframe .s_text_image img",
};

function setOriginalImageFormat(originalFormat = "image/jpeg") {
    return setImageFormat(undefined, true, originalFormat);
}

function setImageFormat(targetFormat, isOriginalFormat = false, originalFormat = "image/jpeg") {
    let formatSelector, postCheck;
    if (isOriginalFormat) {
        formatSelector = "we-button:last-child";
        postCheck = {
            content: "Wait for image update: back to original image",
            trigger: `iframe .s_text_image img[src^="data:${originalFormat};base64,"]`,
            isCheck: true,
        };
    } else {
        formatSelector = `we-button[data-select-format="${targetFormat}"]`;
        postCheck = {
            content: "Wait for image update: NOT original image",
            trigger: 'iframe .s_text_image img:not([src$="s_text_image_default_image"])',
            isCheck: true,
        };
    }

    return [
        selectImage,
        {
            content: "Open format select",
            trigger: 'we-customizeblock-options:has(we-title:contains("Image")) we-select[data-name="format_select_opt"]',
        },
        {
            content: "Select 128 image/webp",
            trigger: `we-customizeblock-options:has(we-title:contains("Image")) we-select[data-name="format_select_opt"] ${formatSelector}`,
        },
        postCheck,
    ];
}

function setImageShape() {
    return [
        selectImage,
        {
            content: "Open shape select",
            trigger: 'we-customizeblock-options:has(we-title:contains("Image")) we-select[data-name="shape_img_opt"]',
        },
        {
            content: "Open shape select",
            trigger: 'we-customizeblock-options:has(we-title:contains("Image")) we-select[data-name="shape_img_opt"] we-button[data-select-label="Diamond"]',
        },
        {
            content: "Wait for image update: svg wrap",
            trigger: 'iframe .s_text_image img[src^="data:image/svg+xml;base64,"]',
            isCheck: true,
        }
    ];
}

function removeImageShape(targetMimetype) {
    return [
        selectImage,
        {
            content: "Remove image shape",
            trigger: 'we-customizeblock-options:has(we-title:contains("Image")) we-button[data-set-img-shape=""]'
        },
        {
            content: `Wait for image update: mimetype ${targetMimetype}`,
            trigger: `iframe .s_text_image img[src^="data:${targetMimetype};base64,"]`,
            isCheck: true,
        }
    ];
}

function cropImage(targetMimetype) {
    return [
        selectImage,
        {
            content: "Open crop widget",
            trigger: 'we-customizeblock-options:has(we-title:contains("Image")) we-button[data-crop="true"]',
        },
        {
            content: "Choose 1/1 crop ratio",
            trigger: '[data-action="ratio"][data-value="1/1"]',
        },
        {
            content: "Apply",
            trigger: '[data-action="apply"]',
        },
        {
            content: `Wait for image update: mimetype ${targetMimetype}`,
            trigger: `iframe .s_text_image img[src^="data:${targetMimetype};base64,"]`,
            isCheck: true,
        }
    ];
}

function testImageMimetypeIs(targetMimetype, originalMimetype) {
    return [
        {
            content: `Check image mimetype before save is ${targetMimetype}`,
            trigger: "iframe .o_modified_image_to_save",
            run() {
                const actualMimetype = this.$anchor[0].dataset.mimetype;
                const expectedMimetype = targetMimetype;
                if (actualMimetype !== expectedMimetype) {
                    console.error(`Wrong image mimetype: ${actualMimetype} - Expected: ${expectedMimetype}`);
                }
            },
        },
        ...wTourUtils.clickOnSave(),
        {
            content: `Check image mimetype after save is ${targetMimetype}`,
            trigger: `iframe img[data-mimetype-before-conversion="${originalMimetype}"]`,
            run() {
                const actualMimetype = this.$anchor[0].dataset.mimetype;
                const expectedMimetype = targetMimetype;
                if (actualMimetype !== expectedMimetype) {
                    console.error(`Wrong image mimetype: ${actualMimetype} - Expected: ${expectedMimetype}`);
                }
            },
        },
        ...wTourUtils.clickOnEditAndWaitEditMode(),
    ];
}

function testImageSnippet(imageFormat, originalMimetype, targetMimetype, firstTargetMimetype = targetMimetype) {
    return [
        ...setImageFormat(imageFormat),
        ...testImageMimetypeIs(firstTargetMimetype, originalMimetype),

        ...setOriginalImageFormat(),
        ...testImageMimetypeIs(originalMimetype, originalMimetype),

        ...setImageFormat(imageFormat),

        ...setImageShape(),
        ...testImageMimetypeIs("image/svg+xml", originalMimetype),

        ...removeImageShape(targetMimetype),
        ...testImageMimetypeIs(targetMimetype, originalMimetype),

        ...cropImage(targetMimetype),
        ...testImageMimetypeIs(targetMimetype, originalMimetype),
    ];
}

wTourUtils.registerWebsitePreviewTour("website_image_mimetype", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_text_image",
        name: "Text - Image",
    }),
    ...testImageSnippet("128 image/webp", "image/jpeg", "image/webp"),
]);

wTourUtils.registerWebsitePreviewTour("website_image_mimetype_no_webp", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    mockCanvasToDataURLStep,
    wTourUtils.dragNDrop({
        id: "s_text_image",
        name: "Text - Image",
    }),
    ...testImageSnippet("128 image/jpeg", "image/jpeg", "image/jpeg"),
]);

wTourUtils.registerWebsitePreviewTour("website_image_mimetype_bigger_output", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    wTourUtils.dragNDrop({
        id: "s_text_image",
        name: "Text - Image",
    }),
    {
        ...selectImage,
        run: "dblclick",
    },
    ...uploadImageFromDialog("image/png", "o.png", PNG_THAT_CONVERTS_TO_BIGGER_WEBP, false, selectImage.trigger),
    ...testImageSnippet("1 image/webp", "image/png", "image/png", "image/webp"),
]);

function testImageGallerySnippet(imageData, targetMimetype) {
    return [
        wTourUtils.dragNDrop({
            id: "s_image_gallery",
            name: "Image Gallery",
        }),
        {
            content: "Open snippet options",
            trigger: "iframe .s_image_gallery img",
        },
        {
            content: "Click on Images - Add button",
            trigger: 'we-button[data-add-images="true"]',
        },
        ...uploadImageFromDialog(
            "image/png",
            "o.png",
            imageData,
        ),
        {
            content: "Navigate to last carousel image",
            trigger: 'iframe [data-bs-slide-to="3"]',
        },
        ...testImageMimetypeIs(targetMimetype, "image/png"),
    ];
}

wTourUtils.registerWebsitePreviewTour("website_image_mimetype_image_gallery", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...testImageGallerySnippet(generateTestPng(1024).split(",")[1], "image/webp"),
]);

wTourUtils.registerWebsitePreviewTour("website_image_mimetype_image_gallery_no_webp", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    mockCanvasToDataURLStep,
    ...testImageGallerySnippet(generateTestPng(1024).split(",")[1], "image/png"),
]);

wTourUtils.registerWebsitePreviewTour("website_image_mimetype_image_gallery_bigger_output", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...testImageGallerySnippet(PNG_THAT_CONVERTS_TO_BIGGER_WEBP, "image/png"),
]);
