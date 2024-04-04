/** @odoo-module */

import weUtils from 'web_editor.utils';
import wTourUtils from 'website.tour_utils';

const snippets = [
    {
        id: 's_text_image',
        name: 'Text - Image',
    },
];
const gradients = [
    'linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
    'linear-gradient(135deg, rgb(255, 222, 202) 0%, rgb(202, 115, 69) 100%)',
];

function typeToName(xType) {
    return xType === 'cc' ? 'color combinations' : xType === 'bg' ? 'background colors' : 'gradients';
}

function switchTo(type, _name) {
    const target = type === 'cc' ? 'color-combinations' : type === 'bg' ? 'custom-colors' : 'gradients';
    const name = _name || typeToName(type);
    return {
        trigger: `.o_we_colorpicker_switch_pane_btn[data-target="${target}"]`,
        content: `Switch to ${name}`,
    };
}

function addCheck(steps, checkX, checkNoX, xType, noSwitch = false) {
    if (!checkX && !checkNoX) {
        return;
    }

    const name = typeToName(xType);
    const selectorCheckX = checkX && `.o_we_color_btn[data-color="${checkX}"].selected`;
    const selectorCheckNoX = checkNoX && `.o_we_color_btn[data-color="${checkNoX}"]:not(.selected)`;
    const step = {
        trigger: selectorCheckX || selectorCheckNoX,
        content: `The correct ${name} is marked as selected`,
        position: 'bottom',
        run: () => null,
    };
    if (!selectorCheckX && selectorCheckNoX) {
        step.extra_trigger = selectorCheckNoX;
    }

    if (!noSwitch) {
        steps.push(switchTo(xType, name));
    }
    steps.push(step);
}

function checkAndUpdateBackgroundColor({
    checkCC, checkNoCC,
    checkBg, checkNoBg,
    checkGradient, checkNoGradient,
    changeType, change,
    finalSelector, finalRun
}) {
    const steps = [
        wTourUtils.changeBackgroundColor(),
    ];

    addCheck(steps, checkCC, checkNoCC, 'cc', true);
    addCheck(steps, checkBg, checkNoBg, 'bg');
    addCheck(steps, checkGradient, checkNoGradient, 'gradient');

    if (changeType) {
        steps.push(switchTo(changeType));
        steps.push(wTourUtils.changeOption('ColoredLevelBackground', `.o_we_color_btn[data-color="${change}"]`, 'background color', 'top', true));
        steps.push({
            trigger: finalSelector,
            content: "The selected colors have been applied (CC AND (BG or GRADIENT))",
            position: 'bottom',
            run: finalRun,
        });
    }

    return steps;
}

function updateAndCheckCustomGradient({updateStep, checkGradient}) {
    const steps = [updateStep, {
        trigger: `iframe #wrapwrap section.${snippets[0].id}.o_cc1`,
        content: 'Color combination 1 still selected',
        run: () => null,
    }];
    addCheck(steps, checkGradient, checkGradient !== gradients[0] && gradients[0], 'gradient', true);
    return steps;
}

wTourUtils.registerWebsitePreviewTour('snippet_background_edition', {
    url: '/',
    edition: true,
    test: true,
},
[
wTourUtils.dragNDrop(snippets[0]),
wTourUtils.clickOnSnippet(snippets[0]),

// Add a color combination
...checkAndUpdateBackgroundColor({
    changeType: 'cc',
    change: 3,
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc3:not([class*=bg-]):not([style*="background"])`,
}),

// Change the color combination + Check the previous one was marked as selected
...checkAndUpdateBackgroundColor({
    checkCC: 3,
    changeType: 'cc',
    change: 2,
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc2:not(.o_cc3):not([class*=bg-])`,
}),

// Check the color combination was marked as selected + Edit the bg color
...checkAndUpdateBackgroundColor({
    checkCC: 2,
    checkNoCC: 3,
    changeType: 'bg',
    change: 'black-50',
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc2.bg-black-50`,
}),

// Check the current color palette selection + Change the bg color
...checkAndUpdateBackgroundColor({
    checkCC: 2,
    checkBg: 'black-50',
    changeType: 'bg',
    change: '800',
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc2.bg-800:not(.bg-black-50)`,
}),

// Check the current color palette selection + Change the color combination
// again. It should keep the bg color class.
...checkAndUpdateBackgroundColor({
    checkCC: 2,
    checkBg: '800',
    checkNoBg: 'black-50',
    changeType: 'cc',
    change: 4,
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc4:not(.o_cc2).bg-800`,
}),

// Check the current color palette status + Replace the bg color by a gradient
...checkAndUpdateBackgroundColor({
    checkCC: 4,
    checkNoCC: 2,
    checkBg: '800',
    changeType: 'gradient',
    change: gradients[0],
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc4:not(.bg-800)[style*="background-image: ${gradients[0]}"]`,
}),

// Check the current color palette status + Replace the gradient
...checkAndUpdateBackgroundColor({
    checkCC: 4,
    checkNoBg: '800',
    checkGradient: gradients[0],
    changeType: 'gradient',
    change: gradients[1],
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc4[style*="background-image: ${gradients[1]}"]:not([style*="background-image: ${gradients[0]}"])`,
}),

// Check the current color palette selection + Change the color combination
// again. It should keep the gradient.
...checkAndUpdateBackgroundColor({
    checkCC: 4,
    checkGradient: gradients[1],
    checkNoGradient: gradients[0],
    changeType: 'cc',
    change: 1,
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc1:not(.o_cc4)[style*="background-image: ${gradients[1]}"]`,
}),

// Final check of the color status in the color palette
...checkAndUpdateBackgroundColor({
    checkCC: 1,
    checkNoCC: 4,
    checkGradient: gradients[1],
}),

// Now, add an image on top of that color combination + gradient
{
    // Close the palette before selecting a media.
    trigger: '.snippet-option-ColoredLevelBackground we-title',
    content: 'Close palette',
},
wTourUtils.changeOption('ColoredLevelBackground', '[data-name="bg_image_toggle_opt"]'),
{
    trigger: '.o_existing_attachment_cell img',
    content: "Select an image in the media dialog",
},
{
    trigger: `iframe .${snippets[0].id}.o_cc.o_cc1`,
    run: function () {
        const parts = weUtils.backgroundImageCssToParts(this.$anchor.css('background-image'));
        if (!parts.url || !parts.url.startsWith('url(')) {
            console.error('An image should have been added as background.');
        }
        if (parts.gradient !== gradients[1]) {
            console.error('The gradient should have been kept when adding the background image');
        }
    },
},

// Replace the gradient while there is a background-image
...checkAndUpdateBackgroundColor({
    checkCC: 1,
    checkGradient: gradients[1],
    changeType: 'gradient',
    change: gradients[0],
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc1:not([style*="${gradients[1]}"])`,
    finalRun: function () {
        const parts = weUtils.backgroundImageCssToParts(this.$anchor.css('background-image'));
        if (!parts.url || !parts.url.startsWith('url(')) {
            console.error('The image should have been kept when changing the gradient');
        }
        if (parts.gradient !== gradients[0]) {
            console.error('The gradient should have been changed');
        }
    },
}),

// Customize gradient
wTourUtils.changeBackgroundColor(),
switchTo('gradient'),
// Avoid navigating across tabs to maintain current editor state
// Step colors
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker .o_custom_gradient_scale',
        content: 'Add step',
        run: 'click',
    },
    checkGradient: 'linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
}),
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker .o_slider_multi input.active',
        content: 'Move step',
        run: () => {
            const slider = $('.colorpicker .o_slider_multi input.active');
            slider.val(45);
            slider.trigger('click');
        },
    },
    checkGradient: 'linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(203, 94, 238) 45%, rgb(75, 225, 236) 100%)',
}),
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker .o_color_picker_inputs .o_hex_div input',
        content: 'Pick step color',
        run: 'text #FF0000',
    },
    checkGradient: 'linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(255, 0, 0) 45%, rgb(75, 225, 236) 100%)',
}),
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker .o_remove_color',
        content: 'Delete step',
        run: 'click',
    },
    checkGradient: 'linear-gradient(135deg, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
}),
// Linear
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker input[data-name="angle"]',
        content: 'Change angle',
        run: 'text_blur 50',
    },
    checkGradient: 'linear-gradient(50deg, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
}),
// Radial
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker we-button[data-gradient-type="radial-gradient"]',
        content: 'Switch to Radial',
        run: 'click',
    },
    checkGradient: 'radial-gradient(circle farthest-side at 25% 25%, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
}),
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker input[data-name="positionX"]',
        content: 'Change X position',
        run: 'text_blur 33',
    },
    checkGradient: 'radial-gradient(circle farthest-side at 33% 25%, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
}),
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker input[data-name="positionY"]',
        content: 'Change Y position',
        run: 'text_blur 75',
    },
    checkGradient: 'radial-gradient(circle farthest-side at 33% 75%, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
}),
...updateAndCheckCustomGradient({
    updateStep: {
        trigger: '.colorpicker we-button[data-gradient-size="closest-side"]',
        content: 'Change color spread size',
        run: 'click',
    },
    checkGradient: 'radial-gradient(circle closest-side at 33% 75%, rgb(203, 94, 238) 0%, rgb(75, 225, 236) 100%)',
}),
// Revert to predefined gradient
{
    trigger: `.o_we_color_btn[data-color="${gradients[0]}"]`,
    content: `Revert to predefiend gradient ${gradients[0]}`,
    run: 'click',
},

// Replace the gradient by a bg color
...checkAndUpdateBackgroundColor({
    checkCC: 1,
    checkGradient: gradients[0],
    checkNoGradient: gradients[1],
    changeType: 'bg',
    change: 'black-75',
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc1.bg-black-75[style^="background-image: url("]:not([style*="${gradients[0]}"])`
}),

// Re-add a gradient
...checkAndUpdateBackgroundColor({
    checkCC: 1,
    checkBg: 'black-75',
    checkNoGradient: gradients[0],
    changeType: 'gradient',
    change: gradients[1],
    finalSelector: `iframe .${snippets[0].id}.o_cc.o_cc1:not(.bg-black-75)`,
    finalRun: function () {
        const parts = weUtils.backgroundImageCssToParts(this.$anchor.css('background-image'));
        if (!parts.url || !parts.url.startsWith('url(')) {
            console.error('The image should have been kept when re-adding the gradient');
        }
        if (parts.gradient !== gradients[1]) {
            console.error('The gradient should have been re-added');
        }
    },
}),

// Final check of color selection and removing the image
...checkAndUpdateBackgroundColor({
    checkCC: 1,
    checkNoBg: 'black-75',
    checkGradient: gradients[1],
}),
wTourUtils.changeOption('ColoredLevelBackground', '[data-name="bg_image_toggle_opt"]', 'image toggle', 'top', true),
{
    trigger: `iframe .${snippets[0].id}.o_cc.o_cc1[style*="background-image: ${gradients[1]}"]`,
    run: () => null,
},

// Now removing all colors via the 'None' button (note: colorpicker still opened)
{
    trigger: '.o_colorpicker_reset',
    content: "Click on the None button of the color palette",
},
{
    trigger: `iframe .${snippets[0].id}:not(.o_cc):not(.o_cc1):not([style*="background-image"])`,
    content: "All color classes and properties should have been removed",
    run: () => null,
}
]);
