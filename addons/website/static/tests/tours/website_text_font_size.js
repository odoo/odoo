/** @odoo-module **/

import wTourUtils from '@website/js/tours/tour_utils';
import {FONT_SIZE_CLASSES} from '@web_editor/js/editor/odoo-editor/src/utils/utils';

const classNameInfo = new Map();
classNameInfo.set("display-1-fs", {scssVariableName: "display-1-font-size", start: 80, end: 90});
classNameInfo.set("display-2-fs", {scssVariableName: "display-2-font-size", start: 72, end: 80});
classNameInfo.set("display-3-fs", {scssVariableName: "display-3-font-size", start: 64, end: 70});
classNameInfo.set("display-4-fs", {scssVariableName: "display-4-font-size", start: 56, end: 60});
classNameInfo.set("h1-fs", {scssVariableName: "h1-font-size", start: 48, end: 50});
classNameInfo.set("h2-fs", {scssVariableName: "h2-font-size", start: 40, end: 42});
classNameInfo.set("h3-fs", {scssVariableName: "h3-font-size", start: 32, end: 38});
classNameInfo.set("h4-fs", {scssVariableName: "h4-font-size", start: 24, end: 34});
classNameInfo.set("h5-fs", {scssVariableName: "h5-font-size", start: 20, end: 30});
classNameInfo.set("h6-fs", {scssVariableName: "h6-font-size", start: 16, end: 26});
classNameInfo.set("base-fs", {scssVariableName: "font-size-base", start: 16, end: 26});
classNameInfo.set("o_small-fs", {scssVariableName: "small-font-size", start: 14, end: 24});

function checkComputedFontSize(fontSizeClass, stage) {
    return {
        content: `Check that the computed font size for ${fontSizeClass} is correct`,
        trigger: `iframe #wrap .s_text_block .${fontSizeClass}`,
        run: function () {
            const computedFontSize = parseInt(getComputedStyle(this.$anchor[0]).fontSize);
            const expectedFontSize = classNameInfo.get(fontSizeClass)[stage];
            const gapBetweenSizes = Math.abs(computedFontSize - expectedFontSize);
            const gapTolerance = 7; // Because the font size is responsive.
            if (gapBetweenSizes > gapTolerance) {
                console.error(`When applied class ${fontSizeClass}, the font size is ` +
                    `${computedFontSize} instead of ~${expectedFontSize}`);
            }
        }
    };
}

function getFontSizeTestSteps(fontSizeClass) {
    return [
        wTourUtils.dragNDrop({id: "s_text_block", name: "Text"}),
        {
            content: `[${fontSizeClass}] Click on the text block first paragraph (to auto select)`,
            trigger: "iframe .s_text_block p",
        }, {
            content: `Open the font size dropdown to select ${fontSizeClass}`,
            trigger: "#font-size button",
        }, {
            content: `Select ${fontSizeClass} in the dropdown`,
            trigger: `a[data-apply-class="${fontSizeClass}"]:contains(${classNameInfo.get(fontSizeClass).start})`,
        },
        checkComputedFontSize(fontSizeClass, "start"),
        wTourUtils.goToTheme(),
        {
            content: `Open the collapse to see the font size of ${fontSizeClass}`,
            trigger: `we-collapse:has(we-input[data-variable="` +
            `${classNameInfo.get(fontSizeClass).scssVariableName}"]) we-toggler`,
        }, {
            content: `Check that the setting for ${fontSizeClass} is correct`,
            trigger: `we-input[data-variable="${classNameInfo.get(fontSizeClass).scssVariableName}"]`
                + ` input:propValue("${classNameInfo.get(fontSizeClass).start}")`,
            isCheck: true,
        }, {
            content: `Change the setting value of ${fontSizeClass}`,
            trigger: `[data-variable="${classNameInfo.get(fontSizeClass).scssVariableName}"] input`,
            run: `text_blur ${classNameInfo.get(fontSizeClass).end}`,
        }, {
            content: `[${fontSizeClass}] Go to blocks tab`,
            trigger: ".o_we_add_snippet_btn",
        }, {
            content: `[${fontSizeClass}] Wait to be in blocks tab`,
            trigger: ".o_we_add_snippet_btn.active",
        },
        wTourUtils.goToTheme(),
        {
            content: `Check that the setting of ${fontSizeClass} has been updated`,
            trigger: `we-input[data-variable="${classNameInfo.get(fontSizeClass).scssVariableName}"]`
                + ` input:propValue("${classNameInfo.get(fontSizeClass).end}")`,
            isCheck: true,
        }, {
            content: `Close the collapse to hide the font size of ${fontSizeClass}`,
            trigger: `we-collapse:has(we-input[data-variable=` +
                `"${classNameInfo.get(fontSizeClass).scssVariableName}"]) we-toggler`,
            extra_trigger: `body:not(:has(.o_we_ui_loading))`,
        },
        checkComputedFontSize(fontSizeClass, "end"),
        {
            content: `Click again on the text with class ${fontSizeClass}`,
            trigger: `iframe #wrap .s_text_block .${fontSizeClass}`,
        }, {
            content: `Remove the text snippet containing the text with class ${fontSizeClass}`,
            trigger: `.oe_snippet_remove`,
        }
    ];
}

function getAllFontSizesTestSteps() {
    const steps = [];
    for (const fontSizeClass of FONT_SIZE_CLASSES) {
        if (fontSizeClass === 'h6-fs') {
            // That option is hidden by default because same value as base-fs
            continue;
        }
        if (fontSizeClass === 'small') {
            // There is nothing related to that class in the UI to test anymore.
            continue;
        }
        steps.push(...getFontSizeTestSteps(fontSizeClass));
    }
    return steps;
}

wTourUtils.registerWebsitePreviewTour("website_text_font_size", {
    test: true,
    url: "/",
    edition: true,
}, () => [
    ...getAllFontSizesTestSteps(),
    // The last step has to be a check.
    {
        content: "Verify that the text block has been deleted",
        trigger: "iframe #wrap:not(:has(.s_text_block))",
        isCheck: true,
    },
]);
