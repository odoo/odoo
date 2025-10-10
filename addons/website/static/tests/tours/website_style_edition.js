import { areCssValuesEqual } from "@html_builder/utils/utils_css";
import { rgbToHex } from "@web/core/utils/colors";
import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    goBackToBlocks,
    goToTheme,
    insertSnippet,
    openLinkPopup,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';

const TARGET_FONT_SIZE = 20; // The max to not be impacted by the responsive font size system
const TARGET_BODY_BG_COLOR = '#00FF00';
const TARGET_BODY_BG_COLOR_V2 = 'rgb(0, 255, 0)';
const TARGET_BODY_COLOR = '#FF00FF';
const TARGET_BODY_COLOR_V2 = 'rgb(255, 0, 255)';
const TARGET_OCC = {
    occ1_primary: "#FF0000",
    occ1_primary_border: "#CE0000",
    occ1_secondary: "#FF9C00",
    occ1_secondary_border: "#BD9400",
    occ2_primary: "#00FFFF",
    occ2_primary_border: "#085294",
    occ2_secondary: "#9C00FF",
    occ2_secondary_border: "#6BADDE",
};

const checkFontSize = function () {
    const style = document.defaultView.getComputedStyle(this.anchor);
    if (!areCssValuesEqual(style.fontSize, `${TARGET_FONT_SIZE}px`, "font-size", style)) {
        console.error(`Expected the font-size to be equal to ${TARGET_FONT_SIZE}px but found ${style.fontSize} instead`);
    }
};
const checkBodyBgColor = function () {
    const style = document.defaultView.getComputedStyle(this.anchor);
    if (!areCssValuesEqual(style.backgroundColor, `${TARGET_BODY_BG_COLOR}`, "background-color", style)) {
        console.error(`Expected the background color to be equal to ${TARGET_BODY_BG_COLOR} but found ${style.backgroundColor} instead`);
    }
};
const checkBodyColor = function () {
    const style = document.defaultView.getComputedStyle(this.anchor);
    if (!areCssValuesEqual(style.color, `${TARGET_BODY_COLOR}`, "color", style)) {
        console.error(`Expected the color to be equal to ${TARGET_BODY_COLOR} but found ${style.color} instead`);
    }
};
const checkPopoverStyling = function (selector, toCheck, checkWith, isBorder) {
    return {
        trigger: `.o_popover .o-dropdown-item .btn:contains(${selector}), .o_popover .o-dropdown-item span:contains(${selector})`,
        run(helper) {
            let rgbColor = "";
            if (isBorder) {
                // Fetch rgb value from border styling
                const regex = /rgb\(\d+,\s*\d+,\s*\d+\)/;
                rgbColor = helper.anchor.style[toCheck].match(regex)[0];
            } else {
                rgbColor = helper.anchor.style[toCheck];
            }
            const hexColor = rgbToHex(rgbColor).toUpperCase();
            if (hexColor !== checkWith) {
                console.error(
                    `Expected the color to be equal to ${checkWith} but found ${hexColor} instead`
                );
            }
        },
    };
};
const changeThemeColor = function (presetNumber = 1, datalabel, value, colorPickerIndex = 1) {
    return [
        {
            content: "Open the color combinations area",
            trigger: "div[data-label='Color Presets'] button",
            run(helper) {
                if (!helper.anchor.classList.contains("active")) {
                    helper.click();
                }
            },
        },
        {
            content: "Open a color combination",
            trigger: `div[id^='builder_collapse_content'] .hb-row:nth-child(${presetNumber}) button.o_hb_collapse_toggler`,
            run: "click",
        },
        {
            content: `Edit the color of that color ${datalabel}`,
            trigger: `div[id^='builder_collapse_content'] .hb-row[data-label='${datalabel}'] .hb-row-content .o_we_color_preview:nth-child(${colorPickerIndex})`,
            run: "click",
        },
        {
            content: "Choose a color",
            trigger: `.o_font_color_selector .o_color_button[data-color="${value}"]`,
            run: "click",
        },
        {
            content: "Close the color combination",
            trigger: `div[id^='builder_collapse_content'] .hb-row:nth-child(${presetNumber}) button.o_hb_collapse_toggler`,
            run: "click",
        },
    ];
};
const setThemePreset = function (selector, optionContainerTitle, presetNumber) {
    return [
        {
            content: `Set preset value of ${optionContainerTitle}`,
            trigger: `:iframe ${selector}`,
            run: "click",
        },
        {
            content: "Open color picker",
            trigger: `[data-container-title='${optionContainerTitle}'] .we-bg-options-container .o_we_color_preview`,
            run: "click",
        },
        {
            content: `Select ${presetNumber} preset`,
            trigger: `button.o_cc${presetNumber}`,
            run: "click",
        },
    ];
};

registerWebsitePreviewTour("website_style_edition", {
    url: '/',
    edition: true,
}, () => [
...goToTheme(),
{
    content: "Change font size",
    trigger: "[data-action-param='font-size-base'] input",
    run: `edit ${TARGET_FONT_SIZE} && click body`,
},
{
    // Waiting the CSS to be reloaded: the code adds a new assets bundle with
    // a #t=... at the end then removes the old one.
    trigger: ':iframe html:not(:has(link[href$="web.assets_frontend.min.css"]))',
},
{
    content: "Check the font size was properly adapted",
    trigger: ':iframe #wrapwrap',
    run: checkFontSize,
}, {
    content: "Open the color combinations area",
    trigger: "div[data-label='Color Presets'] button",
    run: "click",
}, {
    content: "Open a color combination",
    trigger: "div[id^='builder_collapse_content'] button.o_hb_collapse_toggler",
    run: "click",
}, {
    content: "Edit the background color of that color combination",
    trigger: "div[id^='builder_collapse_content'] div .o_we_color_preview",
    run: "click",
}, {
    content: "Choose a color",
    trigger: `.o_font_color_selector .o_color_button[data-color="${TARGET_BODY_BG_COLOR}"]`,
    run: "click",
},
{
    trigger: `
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_BG_COLOR}"],
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_BG_COLOR_V2}"]
    `,
},
{
    content: "Check the body background color was properly adapted",
    trigger: ':iframe body',
    run: checkBodyBgColor,
}, {
    content: "Edit the text color of that color combination",
    trigger: "div[id^='builder_collapse_content'] div[data-label='Text'] .o_we_color_preview",
    run: "click",
}, {
    content: "Choose a color",
    trigger: `.o_font_color_selector .o_color_button[data-color="${TARGET_BODY_COLOR}"]`,
    run: "click",
},
{
    trigger: `
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_COLOR}"],
        div[id^='builder_collapse_content'] div .o_we_color_preview[style*="${TARGET_BODY_COLOR_V2}"]
    `,
},
{
    content: "Check the body color was properly adapted",
    trigger: ':iframe body',
    run: checkBodyColor,
},
...clickOnSave(),
{
    content: "Check the font size is still ok outside of edit mode",
    trigger: ':iframe body #wrapwrap',
    run: checkFontSize,
}, {
    content: "Check the body background color is still ok outside of edit mode",
    trigger: ':iframe body',
    run: checkBodyBgColor,
}, {
    content: "Check the body color is still ok outside of edit mode",
    trigger: ':iframe body',
    run: checkBodyColor,
},
...clickOnEditAndWaitEditMode(),
...goToTheme(),
{
    trigger: "div[data-label='Background'] button[data-action-value='NONE'].active",
},
{
    content: "Click on the Background Image selection",
    trigger: "div[data-label='Background'] button[data-action-value='image']:not(.active)",
    run: "click",
}, {
    content: "The media dialog should open",
    trigger: '.o_select_media_dialog',
}]);

registerWebsitePreviewTour(
    "website_link_popover_preview",
    {
        url: "/",
        edition: true,
    },
    () => [
        ...goToTheme(),
        ...changeThemeColor(1, "Primary Buttons", TARGET_OCC.occ1_primary),
        ...changeThemeColor(1, "Primary Buttons", TARGET_OCC.occ1_primary_border, 2),
        ...changeThemeColor(1, "Secondary Buttons", TARGET_OCC.occ1_secondary),
        ...changeThemeColor(1, "Secondary Buttons", TARGET_OCC.occ1_secondary_border, 2),
        ...changeThemeColor(2, "Primary Buttons", TARGET_OCC.occ2_primary),
        ...changeThemeColor(2, "Primary Buttons", TARGET_OCC.occ2_primary_border, 2),
        ...changeThemeColor(2, "Secondary Buttons", TARGET_OCC.occ2_secondary),
        ...changeThemeColor(2, "Secondary Buttons", TARGET_OCC.occ2_secondary_border, 2),
        goBackToBlocks(),
        // Verify preset values on s_text_cover snippet when the parent element
        // has a higher cc value than its child
        ...insertSnippet({
            id: "s_text_cover",
            name: "Text Cover",
            groupName: "Intro",
        }),
        ...setThemePreset(".s_text_cover .o_grid_mode", "Text Cover", "2"),
        ...setThemePreset(".s_text_cover .o_grid_mode > .o_grid_item", "Column", "1"),
        ...openLinkPopup(
            ":iframe .s_text_cover a.btn:contains('Contact Us')",
            "Contact Us",
            1,
            true
        ),
        {
            trigger: ".o_we_edit_link",
            run: "click",
        },
        {
            trigger: "button[name=link_type]",
            run: "click",
        },
        checkPopoverStyling("Button Primary", "backgroundColor", TARGET_OCC.occ2_primary),
        checkPopoverStyling("Button Primary", "border", TARGET_OCC.occ2_primary_border, true),
        checkPopoverStyling("Button Secondary", "backgroundColor", TARGET_OCC.occ2_secondary),
        checkPopoverStyling("Button Secondary", "border", TARGET_OCC.occ2_secondary_border, true),
        // Verify preset values on footer snippet when the parent element
        // has a hight cc value than its child
        ...setThemePreset("footer", "Footer", "2"),
        ...setThemePreset("footer #connect", "Column", "1"),
        ...openLinkPopup(":iframe footer #connect a:contains('Contact Us')", "Contact Us", 1, true),
        {
            trigger: ".o_we_edit_link",
            run: "click",
        },
        {
            trigger: "button[name=link_type]",
            run: "click",
        },
        checkPopoverStyling("Button Primary", "backgroundColor", TARGET_OCC.occ2_primary),
        checkPopoverStyling("Button Primary", "border", TARGET_OCC.occ2_primary_border, true),
        checkPopoverStyling("Button Secondary", "backgroundColor", TARGET_OCC.occ2_secondary),
        checkPopoverStyling("Button Secondary", "border", TARGET_OCC.occ2_secondary_border, true),
        // Verify preset values on s_text_cover snippet when the parent element
        // has a lower cc value than its child
        ...setThemePreset(".s_text_cover .o_grid_mode", "Text Cover", "1"),
        ...setThemePreset(".s_text_cover .o_grid_mode > .o_grid_item", "Column", "2"),
        ...openLinkPopup(
            ":iframe .s_text_cover a.btn:contains('Contact Us')",
            "Contact Us",
            1,
            true
        ),
        {
            trigger: ".o_we_edit_link",
            run: "click",
        },
        {
            trigger: "button[name=link_type]",
            run: "click",
        },
        checkPopoverStyling("Button Primary", "backgroundColor", TARGET_OCC.occ2_primary),
        checkPopoverStyling("Button Primary", "border", TARGET_OCC.occ2_primary_border, true),
        checkPopoverStyling("Button Secondary", "backgroundColor", TARGET_OCC.occ2_secondary),
        checkPopoverStyling("Button Secondary", "border", TARGET_OCC.occ2_secondary_border, true),
    ]
);
