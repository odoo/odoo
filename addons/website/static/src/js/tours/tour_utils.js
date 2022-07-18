odoo.define("website.tour_utils", function (require) {
"use strict";

const {_t} = require("web.core");
const {Markup} = require('web.utils');
var tour = require("web_tour.tour");

function addMedia(position = "right") {
    return {
        trigger: `.modal-content footer .btn-primary`,
        content: Markup(_t("<b>Add</b> the selected image.")),
        position: position,
        run: "click",
    };
}
function assertPathName(pathName, trigger) {
    return {
        content: `Check if we have been redirected to ${pathName}`,
        trigger: trigger,
        run: () => {
            if (!window.location.pathname.startsWith(pathName)) {
                console.error(`We should be on ${pathName}.`);
            }
        }
    };
}

function changeBackground(snippet, position = "bottom") {
    return {
        trigger: ".o_we_customize_panel .o_we_bg_success",
        content: Markup(_t("<b>Customize</b> any block through this menu. Try to change the background image of this block.")),
        position: position,
        run: "click",
    };
}

function changeBackgroundColor(position = "bottom") {
    return {
        trigger: ".o_we_customize_panel .o_we_color_preview",
        content: Markup(_t("<b>Customize</b> any block through this menu. Try to change the background color of this block.")),
        position: position,
        run: "click",
    };
}

function selectColorPalette(position = "left") {
    return {
        trigger: ".o_we_customize_panel .o_we_so_color_palette we-selection-items",
        alt_trigger: ".o_we_customize_panel .o_we_color_preview",
        content: Markup(_t(`<b>Select</b> a Color Palette.`)),
        position: position,
        run: 'click',
        location: position === 'left' ? '#oe_snippets' : undefined,
    };
}

function changeColumnSize(position = "right") {
    return {
        trigger: `.oe_overlay.ui-draggable.o_we_overlay_sticky.oe_active .o_handle.e`,
        content: Markup(_t("<b>Slide</b> this button to change the column size.")),
        position: position,
    };
}

function changeIcon(snippet, index = 0, position = "bottom") {
    return {
        trigger: `#wrapwrap .${snippet.id} i:eq(${index})`,
        extra_trigger: "body.editor_enable",
        content: Markup(_t("<b>Double click on an icon</b> to change it with one of your choice.")),
        position: position,
        run: "dblclick",
    };
}

function changeImage(snippet, position = "bottom") {
    return {
        trigger: snippet.id ? `#wrapwrap .${snippet.id} img` : snippet,
        extra_trigger: "body.editor_enable",
        content: Markup(_t("<b>Double click on an image</b> to change it with one of your choice.")),
        position: position,
        run: "dblclick",
    };
}

/**
    wTourUtils.changeOption('HeaderTemplate', '[data-name="header_alignment_opt"]', _t('alignment')),
    By default, prevents the step from being active if a palette is opened.
    Set allowPalette to true to select options within a palette.
*/
function changeOption(optionName, weName = '', optionTooltipLabel = '', position = "bottom", allowPalette = false) {
    const noPalette = allowPalette ? '' : '.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened))';
    const option_block = `${noPalette} we-customizeblock-option[class='snippet-option-${optionName}']`;
    return {
        trigger: `${option_block} ${weName}, ${option_block} [title='${weName}']`,
        content: Markup(_.str.sprintf(_t("<b>Click</b> on this option to change the %s of the block."), optionTooltipLabel)),
        position: position,
        run: "click",
    };
}

function selectNested(trigger, optionName, alt_trigger = null, optionTooltipLabel = '', position = "top", allowPalette = false) {
    const noPalette = allowPalette ? '' : '.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened))';
    const option_block = `${noPalette} we-customizeblock-option[class='snippet-option-${optionName}']`;
    return {
        trigger: trigger,
        content: Markup(_.str.sprintf(_t("<b>Select</b> a %s."), optionTooltipLabel)),
        alt_trigger: alt_trigger == null ? undefined : `${option_block} ${alt_trigger}`,
        position: position,
        run: 'click',
        location: position === 'left' ? '#oe_snippets' : undefined,
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
        content: Markup(_.str.sprintf(_t("<b>Slide</b> this button to change the %s padding"), direction)),
        consumeEvent: 'mousedown',
        position: position,
    };
}

/**
 * Click on the top right edit button
 * @param {*} position Where the purple arrow will show up
 */
function clickOnEdit(position = "bottom") {
    return {
        trigger: ".o_menu_systray .o_edit_website_container a",
        content: Markup(_t("<b>Click Edit</b> to start designing your homepage.")),
        extra_trigger: "body:not(.editor_has_snippets)",
        position: position,
        timeout: 30000,
    };
}

/**
 * Simple click on an element in the page.
 * @param {*} elementName
 * @param {*} selector
 */
function clickOnElement(elementName, selector) {
    return {
        content: `Clicking on the ${elementName}`,
        trigger: selector,
        run: 'click'
    };
}

/**
 * Simple click on a snippet in the edition area
 * @param {*} snippet
 * @param {*} position
 */
function clickOnSnippet(snippet, position = "bottom") {
    const snippetClass = snippet.id || snippet;
    return {
        trigger: `iframe #wrapwrap .${snippetClass}`,
        extra_trigger: "body.editor_has_snippets",
        content: Markup(_t("<b>Click on a snippet</b> to access its options menu.")),
        position: position,
        run: "click",
    };
}

function clickOnSave(position = "bottom") {
    return [{
        trigger: "div:not(.o_loading_dummy) > #oe_snippets button[data-action=\"save\"]:not([disabled])",
        extra_trigger: "body:not(:has(.o_dialog))",
        in_modal: false,
        content: Markup(_t("Good job! It's time to <b>Save</b> your work.")),
        position: position,
    }, {
        trigger: 'iframe body:not(.editor_enable)',
        noPrepend: true,
        auto: true, // Just making sure save is finished in automatic tests
        run: () => null,
    }];
}

/**
 * Click on a snippet's text to modify its content
 * @param {*} snippet
 * @param {*} element Target the element which should be rewrite
 * @param {*} position
 */
function clickOnText(snippet, element, position = "bottom") {
    return {
        trigger: snippet.id ? `iframe #wrapwrap .${snippet.id} ${element}` : snippet,
        extra_trigger: "iframe body.editor_enable",
        content: Markup(_t("<b>Click on a text</b> to start editing it.")),
        position: position,
        run: "text",
        consumeEvent: "click",
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
        extra_trigger: ".o_website_preview.editor_enable.editor_has_snippets",
        content: Markup(_.str.sprintf(_t("Drag the <b>%s</b> building block and drop it at the bottom of the page."), snippet.name)),
        position: position,
        // Normally no main snippet can be dropped in the default footer but
        // targeting it allows to force "dropping at the end of the page".
        run: "drag_and_drop iframe #wrapwrap > footer",
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

function goToTheme(position = "bottom") {
    return {
        trigger: '.o_we_customize_theme_btn',
        extra_trigger: '#oe_snippets.o_loaded',
        content: _t("Go to the Theme tab"),
        position: position,
        run: "click",
    };
}

function selectHeader(position = "bottom") {
    return {
        trigger: `iframe header#top`,
        content: Markup(_t(`<b>Click</b> on this header to configure it.`)),
        position: position,
        run: "click",
    };
}

function selectSnippetColumn(snippet, index = 0, position = "bottom") {
     return {
        trigger: `iframe #wrapwrap .${snippet.id} .row div[class*="col-lg-"]:eq(${index})`,
        content: Markup(_t("<b>Click</b> on this column to access its options.")),
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

function getClientActionUrl(path, edition) {
    let url = `/web#action=website.website_preview&path=${encodeURIComponent(path)}`;
    if (edition) {
        url += '&enable_editor=1';
    }
    return url;
}

function clickOnExtraMenuItem(stepOptions, backend = false) {
    return Object.assign({}, {
        content: "Click on the extra menu dropdown toggle if it is there",
        trigger: `${backend ? "iframe" : ""} #top_menu`,
        run: function () {
            const extraMenuButton = this.$anchor[0].querySelector('.o_extra_menu_items a.nav-link');
            if (extraMenuButton) {
                extraMenuButton.click();
            }
        },
    }, stepOptions);
}

/**
 * Registers a tour that will go in the website client action.
 *
 * @param name {string} The tour's name
 * @param options {Object} The tour options
 * @param options.url {string} the page to edit
 * @param options.edition {boolean} If the tour starts in edit mode
 * @param steps {[*]} The steps of the tour
 */
function registerEditionTour(name, options, steps) {
    let tourSteps = steps;
    let url = getClientActionUrl(options.url, !!options.edition);
    if (options.edition) {
        tourSteps = [{
            content: "Wait for the edit mode to be started",
            trigger: '.o_website_preview.editor_enable.editor_has_snippets',
            timeout: 30000,
            run: () => {}, // It's a check
        }].concat(tourSteps);
    }
    tour.register(name, Object.assign(options, { url }), tourSteps);
}

function registerThemeHomepageTour(name, steps) {
    registerEditionTour(name, {
        url: '/',
        edition: true,
        sequence: 1010,
        saveAs: "homepage",
    }, prepend_trigger(
        steps.concat(clickOnSave()),
        ".o_website_preview[data-view-xmlid='website.homepage'] "
    ));
}

function registerBackendAndFrontend(name, options, steps) {
    let url;
    let tourSteps = steps;
    if (window.location.pathname === '/web') {
        url = getClientActionUrl(options.url);
        for (const step of tourSteps) {
            step.trigger = 'iframe ' + step.trigger;
            if (step.extra_trigger) {
                step.extra_trigger = 'iframe ' + step.trigger;
            }
        }
    } else {
        url = options.url;
    }
    tour.register(name, {
        url
    }, tourSteps);
}

/**
 * Selects an element inside a we-select, if the we-select is from a m2o widget, searches for it.
 *
 * @param widgetName {string} The widget's data-name
 * @param elementName {string} the element to search
 * @param searchNeeded {Boolean} if the widget is a m2o widget and a search is needed
 */
function selectElementInWeSelectWidget(widgetName, elementName, searchNeeded = false) {
    const steps = [clickOnElement(`${widgetName} toggler`, `we-select[data-name=${widgetName}] we-toggler`)];

    if (searchNeeded) {
        steps.push({
            content: `Inputing ${elementName} in m2o widget search`,
            trigger: `we-select[data-name=${widgetName}] div.o_we_m2o_search input`,
            run: `text ${elementName}`
        });
    }
    steps.push(clickOnElement(`${elementName} in the ${widgetName} widget`,
        `we-select[data-name=${widgetName}] we-button:contains(${elementName})`));
    return steps;
}

return {
    addMedia,
    assertPathName,
    changeBackground,
    changeBackgroundColor,
    changeColumnSize,
    changeIcon,
    changeImage,
    changeOption,
    changePaddingSize,
    clickOnEdit,
    clickOnElement,
    clickOnSave,
    clickOnSnippet,
    clickOnText,
    dragNDrop,
    goBackToBlocks,
    goToTheme,
    selectColorPalette,
    selectHeader,
    selectNested,
    selectSnippetColumn,
    getClientActionUrl,
    registerThemeHomepageTour,
    clickOnExtraMenuItem,
    registerEditionTour,
    registerBackendAndFrontend,
    selectElementInWeSelectWidget,
};
});
