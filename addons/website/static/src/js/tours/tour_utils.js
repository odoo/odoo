odoo.define("website.tour_utils", function (require) {
"use strict";

const core = require("web.core");
const _t = core._t;

var tour = require("web_tour.tour");

/**

const snippets = [
    {
        id: 's_cover',
        name: 'Cover',
    },
    {
        id: 's_text_image',
        name: 'Text - Image',
    }
];

tour.register("themename_tour", {
    url: "/",
    saveAs: "homepage",
}, [
    wTourUtils.dragNDrop(snippets[0]),
    wTourUtils.clickOnText(snippets[0], 'h1'),
    wTourUtils.changeOption('colorFilter', 'span.o_we_color_preview', _t('color filter')),
    wTourUtils.selectHeader(),
    wTourUtils.changeOption('HeaderTemplate', '[data-name="header_alignment_opt"]', _t('alignment')),
    wTourUtils.goBackToBlocks(),
    wTourUtils.dragNDrop(snippets[1]),
    wTourUtils.changeImage(snippets[1]),
    wTourUtils.clickOnSave(),
]);
**/



function addMedia(position = "right") {
    return {
        trigger: `.modal-content footer .btn-primary`,
        content: _t("<b>Add</b> the selected image."),
        position: position,
        run: "click",
    };
}

function changeBackground(snippet, position = "bottom") {
    return {
        trigger: ".o_we_customize_panel .o_we_edit_image",
        content: _t("<b>Customize</b> any block through this menu. Try to change the background image of this block."),
        position: position,
        run: "click",
    };
}

function changeBackgroundColor(position = "bottom") {
    return {
        trigger: ".o_we_customize_panel .o_we_color_preview",
        content: _t("<b>Customize</b> any block through this menu. Try to change the background color of this block."),
        position: position,
        run: "click",
    };
}

function changeColumnSize(position = "right") {
    return {
        trigger: `.oe_overlay.ui-draggable.o_we_overlay_sticky.oe_active .o_handle.e`,
        content: _t("<b>Slide</b> this button to change the column size."),
        position: position,
    };
}

function changeIcon(snippet, index = 0, position = "bottom") {
    return {
        trigger: `#wrapwrap .${snippet.id} i:eq(${index})`,
        content: _t("<b>Double click on an icon</b> to change it with one of your choice."),
        position: position,
        run: "dblclick",
    };
}

function changeImage(snippet, position = "bottom") {
    return {
        trigger: `#wrapwrap .${snippet.id} img`,
        content: _t("<b>Double click on an image</b> to change it with one of your choice."),
        position: position,
        run: "dblclick",
    };
}

/**
    wTourUtils.changeOption('HeaderTemplate', '[data-name="header_alignment_opt"]', _t('alignment')),
*/
function changeOption(optionName, weName = '', optionTooltipLabel = '', position = "bottom") {
    const option_block = `we-customizeblock-option[class='snippet-option-${optionName}']`
    return {
        trigger: `${option_block} ${weName}, ${option_block} [title='${weName}']`,
        content: _t(`<b>Click</b> on this option to change the ${optionTooltipLabel} of the block.`),
        position: position,
        run: "click",
    };
}

function changePaddingSize(direction) {
    let paddingDirection = "n";
    let position = "top";
    if (direction === "bottom") {
        paddingDirection = "s";
        position = "bottom";
    }
    return {
        trigger: `.oe_overlay.ui-draggable.o_we_overlay_sticky.oe_active .o_handle.${paddingDirection}`,
        content: _t(`<b>Slide</b> this button to change the ${direction} padding`),
        position: position,
    };
}

/**
 * Click on the top right edit button
 * @param {*} position Where the purple arrow will show up
 */
function clickOnEdit(position = "bottom") {
    return {
        trigger: "a[data-action=edit]",
        content: _t("<b>Click Edit</b> to start designing your homepage."),
        extra_trigger: ".homepage",
        position: position,
    };
}

/**
 * Simple click on a snippet in the edition area
 * @param {*} snippet
 * @param {*} position
 */
function clickOnSnippet(snippet, position = "bottom") {
    return {
        trigger: `#wrapwrap .${snippet.id}`,
        content: _t("<b>Click on a snippet</b> to access its options menu."),
        position: position,
        run: "click",
    };
}

function clickOnSave(position = "bottom") {
    return {
        trigger: "button[data-action=save]",
        content: _t("Good job! It's time to <b>Save</b> your work."),
        position: position,
    };
}

/**
 * Click on a snippet's text to modify its content
 * @param {*} snippet
 * @param {*} element Target the element which should be rewrite
 * @param {*} position
 */
function clickOnText(snippet, element, position = "bottom") {
    return {
        trigger: `#wrapwrap .${snippet.id} ${element}`,
        content: _t("Even if this title is cool, you can change it. <b>Click on a text</b> to start editing it."),
        position: position,
        run: "text",
        consumeEvent: "input",
    };
}

/**
 * Drag a snippet from the Blocks area and drop it in the Edit area
 * @param {*} snippet contain the id and the name of the targeted snippet
 * @param {*} position Where the purple arrow will show up
 */
function dragNDrop(snippet, position = "bottom") {
    return {
        trigger: `#oe_snippets .oe_snippet[name="${snippet.name}"] .oe_snippet_thumbnail:not(.o_we_already_dragging)`,
        extra_trigger: "body.editor_enable.editor_has_snippets",
        moveTrigger: '.oe_drop_zone',
        content: _t(`Drag the <b>${snippet.name}</b> building block and drop it in your page.`),
        position: position,
        run: "drag_and_drop #wrap",
    };
}

function goBackToBlocks(position = "bottom") {
    return {
        trigger: '.o_we_add_snippet_btn',
        content: _t("Click here to go back to block tab."),
        position: position,
        run: "click",
    };
}

function goToOptions(position = "bottom") {
    return {
        trigger: '.o_we_customize_theme_btn',
        content: _t("Go to the Options tab"),
        position: position,
        run: "click",
    };
}

function selectHeader(position = "bottom") {
    return {
        trigger: `header#top`,
        content: _t(`<b>Click</b> on this header to configure it.`),
        position: position,
        run: "click",
    };
}

function selectSnippetColumn(snippet, index = 0, position = "bottom") {
     return {
        trigger: `#wrapwrap .${snippet.id} .row div[class*="col-lg-"]:eq(${index})`,
        content: _t("<b>Click</b> on this column to access its options."),
         position: position,
        run: "click",
     };
}

function prepend_trigger(steps, prepend_text='') {
    for (const step of steps) {
        if (!step.noPrepend && prepend_text) {
            step.trigger = prepend_text + step.trigger;
        }
    }
    return steps;
}

function registerThemeHomepageTour(name, steps) {
    tour.register(name, {
        url: "/",
        sequence: 1010,
        saveAs: "homepage",
    }, prepend_trigger(
        steps,
        "html[data-view-xmlid='website.homepage'] "
    ));
}


return {
    addMedia,
    changeBackground,
    changeBackgroundColor,
    changeColumnSize,
    changeIcon,
    changeImage,
    changeOption,
    changePaddingSize,
    clickOnEdit,
    clickOnSave,
    clickOnSnippet,
    clickOnText,
    dragNDrop,
    goBackToBlocks,
    goToOptions,
    selectHeader,
    selectSnippetColumn,

    registerThemeHomepageTour,
};
});
