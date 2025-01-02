/** @odoo-module **/

import {
    extractBase64PartFromDataURL,
    extractMimetypeFromDataURL,
} from "@web/core/utils/image_processing";
import {
    generateTestImage,
    mockCanvasToDataURLStep,
    PNG_THAT_CONVERTS_TO_BIGGER_WEBP,
    uploadImageFromDialog,
} from "@website/../tests/tours/snippet_image_mimetype";
import wTourUtils from "@website/js/tours/tour_utils";

function testPngUploadImplicitConversion(testImageData, expectedMimetype) {
    return [
        {
            content: "Click on the first event's cover",
            trigger: "iframe .o_record_cover_component",
        },
        {
            content: "Open add image dialog",
            trigger: ".snippet-option-CoverProperties we-button[data-background].active",
        },
        ...uploadImageFromDialog(expectedMimetype, "fake_file", testImageData, false, undefined),
        ...wTourUtils.clickOnSave(),
        {
            content: `Verify image mimetype is ${expectedMimetype}`,
            trigger: "iframe .o_record_cover_component",
            async run() {
                const cover = this.$anchor[0];

                async function convertToBase64(file) {
                    return await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result);
                        reader.onerror = reject;
                        reader.readAsDataURL(file);
                    });
                }

                const src = cover.style.backgroundImage.split('"')[1];
                const imgBlob = await (await fetch(src)).blob();
                const dataURL = await convertToBase64(imgBlob);
                const mimetype = extractMimetypeFromDataURL(dataURL);
                if (mimetype !== expectedMimetype) {
                    console.error(`Wrong mimetype ${mimetype} - Expected ${expectedMimetype}`);
                }
            },
        },
    ];
}

wTourUtils.registerWebsitePreviewTour(
    "website_event_cover_image_mimetype",
    {
        test: true,
        edition: true,
        url: "/event",
    },
    () => [
        ...testPngUploadImplicitConversion(
            extractBase64PartFromDataURL(generateTestImage(1024, "image/jpeg")),
            "image/webp"
        ),
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_event_cover_image_mimetype_no_webp",
    {
        test: true,
        edition: true,
        url: "/event",
    },
    () => [
        mockCanvasToDataURLStep,
        ...testPngUploadImplicitConversion(
            extractBase64PartFromDataURL(generateTestImage(1024, "image/jpeg")),
            "image/jpeg"
        ),
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_event_cover_image_mimetype_bigger_output",
    {
        test: true,
        edition: true,
        url: "/event",
    },
    () => [...testPngUploadImplicitConversion(PNG_THAT_CONVERTS_TO_BIGGER_WEBP, "image/png")]
);
