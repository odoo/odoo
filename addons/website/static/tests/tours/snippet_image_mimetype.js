/** @odoo-module */

import {
    canExportCanvasAsWebp,
    convertCanvasToDataURL,
    extractBase64PartFromDataURL,
    extractMimetypeFromDataURL,
} from "@web/core/utils/image_processing";
import wTourUtils from "@website/js/tours/tour_utils";

let originalToDataURL;
export const mockCanvasToDataURLStep = {
    content: "Mock HTMLCanvasElement.toDataURL",
    trigger: "body",
    run() {
        originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function (type, quality) {
            return originalToDataURL.call(
                this,
                type === "image/webp" ? "image/png" : type,
                quality
            );
        };
        canExportCanvasAsWebp._canExportCanvasAsWebp = false;
    },
};
export const unmockCanvasToDataURLStep = {
    content: "Unmock HTMLCanvasElement.toDataURL",
    trigger: "body",
    run() {
        HTMLCanvasElement.prototype.toDataURL = originalToDataURL;
        originalToDataURL = undefined;
        canExportCanvasAsWebp._canExportCanvasAsWebp = true;
    },
};

export function uploadImageFromDialog(
    mimetype,
    filename,
    data,
    confirmChoice = true,
    targetSelector = ".o_we_existing_attachments .o_we_attachment_selected img"
) {
    return [
        {
            content: "Upload an image",
            trigger: ".o_upload_media_button",
            async run() {
                const imageData = Uint8Array.from([...atob(data)].map((c) => c.charCodeAt(0)));
                const fileInput = document.querySelector(
                    '.o_select_media_dialog input[type="file"]'
                );
                const file = new File([imageData], filename, { type: mimetype });
                const transfer = new DataTransfer();
                transfer.items.add(file);
                fileInput.files = transfer.files;
                fileInput.dispatchEvent(new Event("change"));
            },
        },
        ...(confirmChoice
            ? [
                  ...wTourUtils.waitForImageToLoad(targetSelector),
                  {
                      content: "Confirm choice",
                      trigger: '.o_select_media_dialog footer button:contains("Add")',
                      extraTrigger: ".o_we_existing_attachments .o_we_attachment_selected",
                  },
              ]
            : []),
    ];
}

export const PNG_THAT_CONVERTS_TO_BIGGER_WEBP =
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVQIW2NgAAIAAAUAAR4f7BQAAAAASUVORK5CYII=";
const DUMMY_WEBP = "UklGRiwAAABXRUJQVlA4TB8AAAAv/8F/EAcQEREQCCT7e89QRP8z/vOf//znP//5z/8BAA==";

export function generateTestImage(size, mimetype) {
    const canvas = document.createElement("canvas");
    canvas.width = size;
    canvas.height = size;
    return canvas.toDataURL(mimetype);
}

const selectTextImageSnippetImage = {
    content: "Select image",
    trigger: "iframe .s_text_image img",
};
const selectImageGallerySnippetImage = {
    content: "Select image",
    trigger: "iframe .s_image_gallery img",
};

function setOriginalImageFormat() {
    return setImageFormat(undefined, true);
}

function setImageFormat(targetFormat, isOriginalFormat = false) {
    const formatSelector = isOriginalFormat
        ? "we-button:last-child"
        : `we-button[data-select-format="${targetFormat}"]`;
    return [
        {
            content: "Open format select",
            trigger: 'we-select[data-name="format_select_opt"]',
        },
        {
            content: `Select ${targetFormat || "original format"}`,
            trigger: `we-select[data-name="format_select_opt"] ${formatSelector}`,
        },
    ];
}

function setImageShape() {
    return [
        {
            content: "Open shape select",
            trigger:
                'we-customizeblock-options:has(we-title:contains("Image")) we-select[data-name="shape_img_opt"]',
        },
        {
            content: "Select diamond shape",
            trigger:
                'we-customizeblock-options:has(we-title:contains("Image")) we-select[data-name="shape_img_opt"] we-button[data-select-label="Diamond"]',
        },
        {
            content: "Wait for image update: svg wrap",
            trigger: 'iframe .s_text_image img[src^="data:image/svg+xml;base64,"]',
            isCheck: true,
        },
    ];
}

function removeImageShape(targetMimetype) {
    return [
        {
            content: "Remove image shape",
            trigger:
                'we-customizeblock-options:has(we-title:contains("Image")) we-button[data-set-img-shape=""]',
        },
        {
            content: `Wait for image update: mimetype ${targetMimetype}`,
            trigger: `iframe .s_text_image img[src^="data:${targetMimetype};base64,"]`,
            isCheck: true,
        },
    ];
}

function cropImage(targetMimetype) {
    return [
        {
            content: "Open crop widget",
            trigger:
                'we-customizeblock-options:has(we-title:contains("Image")) we-button[data-crop="true"]',
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
            content: `Wait for image update: aspect ratio to 1/1`,
            trigger: `iframe .s_text_image img[data-aspect-ratio="1/1"]`,
            isCheck: true,
        },
        {
            content: `Wait for image update: mimetype ${targetMimetype}`,
            trigger: `iframe .s_text_image img[src^="data:${targetMimetype};base64,"]`,
            isCheck: true,
        },
    ];
}

function removeImageCrop(originalMimetype) {
    return [
        {
            content: "Reset crop",
            trigger:
                'we-customizeblock-options:has(we-title:contains("Image")) we-button[data-reset-crop]',
        },
        {
            content: `Wait for image update: reset aspect ratio to 0/0`,
            trigger: `iframe .s_text_image img[data-aspect-ratio="0/0"]`,
            isCheck: true,
        },
        {
            content: `Wait for image update: mimetype ${originalMimetype}`,
            trigger: `iframe .s_text_image img[src^="data:${originalMimetype};base64,"]`,
            isCheck: true,
        },
    ];
}

function testImageMimetypeIs(
    expectedBaseImageMimetype,
    isSvgEmbedded = false,
    trigger = "iframe .o_modified_image_to_save",
    skipDataURLMimetypeCheck = false
) {
    const expectedMimetype = isSvgEmbedded ? "image/svg+xml" : expectedBaseImageMimetype;
    const expectedSvgEmbeddedMimetype = isSvgEmbedded ? expectedBaseImageMimetype : undefined;
    if (!skipDataURLMimetypeCheck) {
        trigger += `[src^="data:${expectedMimetype};base64,"]`;
    }
    return [
        {
            content: `Image data-mimetype is ${expectedMimetype}`,
            trigger: `${trigger}[data-mimetype="${expectedMimetype}"]`,
            isCheck: true,
        },
        {
            content: `Image data-original-mimetype is ${expectedSvgEmbeddedMimetype}`,
            trigger: `${trigger}${
                expectedSvgEmbeddedMimetype
                    ? `[data-original-mimetype="${expectedSvgEmbeddedMimetype}"]`
                    : ":not([data-original-mimetype])"
            }`,
            isCheck: true,
        },
        ...(skipDataURLMimetypeCheck
            ? []
            : [
                  {
                      content: `Image's actual mimetype is ${expectedBaseImageMimetype}`,
                      trigger: trigger,
                      run() {
                          const dataURL = this.$anchor[0].src;
                          let actualMimetype = extractMimetypeFromDataURL(dataURL);
                          if (isSvgEmbedded) {
                              if (actualMimetype !== "image/svg+xml") {
                                  throw new Error(
                                      `Image is not embedded in SVG (Got ${actualMimetype} - Expected: image/svg+xml)`
                                  );
                              }

                              const svgText = atob(extractBase64PartFromDataURL(dataURL));
                              const svg = new DOMParser().parseFromString(
                                  svgText,
                                  "image/svg+xml"
                              ).documentElement;
                              const embeddedDataURL = svg
                                  .querySelector("image")
                                  .getAttribute("xlink:href");
                              actualMimetype = extractMimetypeFromDataURL(embeddedDataURL);
                          }

                          if (actualMimetype !== expectedBaseImageMimetype) {
                              throw new Error(
                                  `Base image dataURL is of the wrong mimetype: Got ${actualMimetype} - Expected: ${expectedBaseImageMimetype}`
                              );
                          }
                      },
                  },
              ]),
    ];
}

function testImageMimetypeBeforeAndAfterSave(
    expectedMimetype,
    mimetypeBeforeConversion,
    selectImageStep,
    isSvgEmbedded = false,
    goBackToEditMode = true
) {
    const postSaveTrigger = `iframe img[data-mimetype-before-conversion="${mimetypeBeforeConversion}"]`;
    return [
        ...testImageMimetypeIs(expectedMimetype, isSvgEmbedded),
        ...wTourUtils.clickOnSave(),
        ...testImageMimetypeIs(expectedMimetype, isSvgEmbedded, postSaveTrigger, true),
        ...(goBackToEditMode ? [...wTourUtils.clickOnEditAndWaitEditMode(), selectImageStep] : []),
    ];
}

const testFormatSnippetOption = (expectedValue) => ({
    content: `Format snippet option is set to ${expectedValue}`,
    trigger: 'we-select[data-name="format_select_opt"] we-toggler',
    run() {
        const actualValue = this.$anchor[0].innerText;
        if (actualValue !== expectedValue) {
            throw new Error(
                `Format snippet option is "${actualValue}" - Expected "${expectedValue}"`
            );
        }
    },
});

function reloadMock(selectImageStep, mockStep = mockCanvasToDataURLStep) {
    return [
        ...wTourUtils.clickOnSave(),
        mockStep,
        ...wTourUtils.clickOnEditAndWaitEditMode(),
        selectImageStep,
    ];
}

function reloadUnmock(selectImageStep) {
    return reloadMock(selectImageStep, unmockCanvasToDataURLStep);
}

function testImageSnippet(imageFormat, originalMimetype, formatMimetype) {
    const testStepOnOff = (
        on,
        off,
        wrapOn = false,
        wrapOff = false,
        overrideOffMimetype = undefined
    ) => {
        const test = (fn, mimetype, wrap, overrideMimetype) => [
            ...fn(wrap ? "image/svg+xml" : overrideMimetype || mimetype),
            ...testImageMimetypeIs(overrideMimetype || mimetype, !!wrap),
        ];
        const testOn = (mimetype) => test(on, mimetype, wrapOn);
        const testOff = (mimetype) => test(off, mimetype, wrapOff, overrideOffMimetype);
        return [
            ...setOriginalImageFormat(),
            ...testOn(originalMimetype),
            ...testOff(originalMimetype),

            ...setImageFormat(imageFormat),
            ...testOn(formatMimetype),
            ...testOff(formatMimetype),

            ...setImageFormat(imageFormat),
            ...testOn(formatMimetype),
            ...setOriginalImageFormat(),
            ...testOff(originalMimetype),

            ...setOriginalImageFormat(),
            ...testOn(originalMimetype),
            ...setImageFormat(imageFormat),
            ...testOff(formatMimetype),
        ];
    };
    return [
        selectTextImageSnippetImage,

        ...setImageFormat(imageFormat),
        ...testImageMimetypeBeforeAndAfterSave(
            formatMimetype,
            originalMimetype,
            selectTextImageSnippetImage
        ),

        ...setOriginalImageFormat(),
        ...testImageMimetypeBeforeAndAfterSave(
            originalMimetype,
            originalMimetype,
            selectTextImageSnippetImage
        ),

        // Image shape
        ...testStepOnOff(setImageShape, removeImageShape, true),

        // Image crop
        ...testStepOnOff(cropImage, removeImageCrop, false, false, formatMimetype),

        // Image crop while shape on
        ...setImageShape(),
        ...testStepOnOff(cropImage, removeImageCrop, true, true, formatMimetype),
        ...removeImageShape(formatMimetype),
    ];
}

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        wTourUtils.dragNDrop({
            id: "s_text_image",
            name: "Text - Image",
        }),
        ...testImageSnippet("128 image/webp", "image/jpeg", "image/webp"),
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_no_webp",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        mockCanvasToDataURLStep,
        wTourUtils.dragNDrop({
            id: "s_text_image",
            name: "Text - Image",
        }),
        ...testImageSnippet("128 image/jpeg", "image/jpeg", "image/jpeg"),
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_bigger_output",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        {
            content: "Verify that the test png data produces a bigger webp as output",
            trigger: "body",
            run: () => {
                const canvas = document.createElement("canvas");
                const input = PNG_THAT_CONVERTS_TO_BIGGER_WEBP;
                const defaultQualityUsedInCode = 0.75; // Should match {@link applyModifications}
                const { dataURL: output } = convertCanvasToDataURL(
                    canvas,
                    "image/webp",
                    defaultQualityUsedInCode
                );
                if (output.length <= input.length) {
                    throw new Error(
                        "Wrong test data: this png should produce a bigger output when converted to webp"
                    );
                }
            },
        },
        wTourUtils.dragNDrop({
            id: "s_text_image",
            name: "Text - Image",
        }),
        {
            ...selectTextImageSnippetImage,
            run: "dblclick",
        },
        ...uploadImageFromDialog(
            "image/png",
            "o.png",
            PNG_THAT_CONVERTS_TO_BIGGER_WEBP,
            false,
            selectTextImageSnippetImage.trigger
        ),
        ...testImageSnippet("1 image/webp", "image/png", "image/png"),
    ]
);

function testImageGallerySnippet(
    imageData,
    originalMimetype,
    targetMimetype,
    waitForModifiedImage = true
) {
    return [
        wTourUtils.dragNDrop({
            id: "s_image_gallery",
            name: "Image Gallery",
        }),
        selectImageGallerySnippetImage,
        {
            content: "Click on Images - Add button",
            trigger: 'we-button[data-add-images="true"]',
        },
        ...uploadImageFromDialog(originalMimetype, "test_image", imageData),
        {
            content: "Navigate to last carousel image",
            trigger: 'iframe [data-bs-slide-to="3"]',
        },
        ...(waitForModifiedImage
            ? testImageMimetypeBeforeAndAfterSave(
                  targetMimetype,
                  originalMimetype,
                  selectImageGallerySnippetImage,
                  false,
                  false
              )
            : testImageMimetypeIs(
                  targetMimetype,
                  false,
                  `iframe .carousel-item.active img[src$="test_image"]`,
                  true
              )),
    ];
}

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_image_gallery",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        ...testImageGallerySnippet(
            extractBase64PartFromDataURL(generateTestImage(1024, "image/jpeg")),
            "image/jpeg",
            "image/webp"
        ),
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_image_gallery_no_webp",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        mockCanvasToDataURLStep,
        ...testImageGallerySnippet(
            extractBase64PartFromDataURL(generateTestImage(1024, "image/jpeg")),
            "image/jpeg",
            "image/jpeg",
            false
        ),
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_image_gallery_bigger_output",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [...testImageGallerySnippet(PNG_THAT_CONVERTS_TO_BIGGER_WEBP, "image/png", "image/png")]
);

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_crop",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        wTourUtils.dragNDrop({
            id: "s_text_image",
            name: "Text - Image",
        }),
        selectTextImageSnippetImage,
        ...setImageFormat("512 image/webp"),

        // Webp -> no webp
        ...cropImage("image/webp"),
        ...testImageMimetypeIs("image/webp"),
        mockCanvasToDataURLStep,
        ...removeImageCrop("image/jpeg"), // !isChanged && Original format is smaller
        ...testImageMimetypeIs("image/jpeg"),
        testFormatSnippetOption("690px (Suggested) jpeg"),
        ...setImageFormat("512 image/jpeg"),

        // No webp -> webp
        ...cropImage("image/jpeg"),
        ...testImageMimetypeIs("image/jpeg"),
        unmockCanvasToDataURLStep,
        ...removeImageCrop("image/webp"),
        ...testImageMimetypeIs("image/webp"),
        testFormatSnippetOption("690px (Suggested) webp"),
    ]
);

wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_shape",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [
        wTourUtils.dragNDrop({
            id: "s_text_image",
            name: "Text - Image",
        }),
        selectTextImageSnippetImage,
        ...setOriginalImageFormat(),
        ...testImageMimetypeIs("image/jpeg"),

        ...setImageShape(),
        ...testImageMimetypeIs("image/jpeg", true),
        ...setImageFormat("512 image/webp"),
        ...testImageMimetypeIs("image/webp", true),
        testFormatSnippetOption("512px webp"),
        ...removeImageShape("image/webp"),
        ...testImageMimetypeIs("image/webp"),
        testFormatSnippetOption("512px webp"),

        // Webp browser -> no webp browser
        ...setImageShape(),
        ...setImageFormat("512 image/webp"),
        ...testImageMimetypeIs("image/webp", true), // Wait for html update
        ...reloadMock(selectTextImageSnippetImage),
        testFormatSnippetOption("512px webp"),
        ...removeImageShape("image/jpeg"),
        ...testImageMimetypeIs("image/jpeg"),
        testFormatSnippetOption("512px jpeg"),

        // No webp browser -> webp browser
        ...setImageShape(),
        ...setImageFormat("512 image/jpeg"),
        ...testImageMimetypeIs("image/jpeg", true),
        testFormatSnippetOption("512px jpeg"),
        ...reloadUnmock(selectTextImageSnippetImage),
        testFormatSnippetOption("512px jpeg"),
        ...removeImageShape("image/webp"),
        ...testImageMimetypeIs("image/webp"),
        testFormatSnippetOption("512px webp"),

        // Set shape webp -> no webp
        ...reloadMock(selectTextImageSnippetImage),
        ...setImageShape(),
        ...testImageMimetypeIs("image/jpeg", true),
        testFormatSnippetOption("512px jpeg"),
    ]
);

const wysiwygSteps = () => [
    {
        content: "Select logo",
        trigger: 'iframe [data-oe-field="logo"] img',
    },
    {
        content: "Replace image button",
        trigger: 'we-button[data-replace-media="true"]',
    },
    ...uploadImageFromDialog("image/webp", "test.webp", DUMMY_WEBP, false),
    ...setOriginalImageFormat(),
    ...wTourUtils.clickOnSave(),
];
wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_wysiwyg",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [...wysiwygSteps()]
);
wTourUtils.registerWebsitePreviewTour(
    "website_image_mimetype_wysiwyg_no_webp",
    {
        test: true,
        url: "/",
        edition: true,
    },
    () => [mockCanvasToDataURLStep, ...wysiwygSteps()]
);
