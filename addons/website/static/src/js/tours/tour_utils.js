/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";

import { markup } from "@odoo/owl";

function addMedia(position = "right") {
    return {
        trigger: `.modal-content footer .btn-primary`,
        content: markup(_t("<b>Add</b> the selected image.")),
        position: position,
        run: "click",
    };
}
function assertCssVariable(variableName, variableValue, trigger = 'iframe body') {
    return {
        content: `Check CSS variable ${variableName}=${variableValue}`,
        trigger: trigger,
        auto: true,
        run: function () {
            const styleValue = getComputedStyle(this.$anchor[0]).getPropertyValue(variableName);
            if ((styleValue && styleValue.trim().replace(/["']/g, '')) !== variableValue.trim().replace(/["']/g, '')) {
                throw new Error(`Failed precondition: ${variableName}=${styleValue} (should be ${variableValue})`);
            }
        },
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
        content: markup(_t("<b>Customize</b> any block through this menu. Try to change the background image of this block.")),
        position: position,
        run: "click",
    };
}

function changeBackgroundColor(position = "bottom") {
    return {
        trigger: ".o_we_customize_panel .o_we_color_preview",
        content: markup(_t("<b>Customize</b> any block through this menu. Try to change the background color of this block.")),
        position: position,
        run: "click",
    };
}

function selectColorPalette(position = "left") {
    return {
        trigger: ".o_we_customize_panel .o_we_so_color_palette we-selection-items",
        alt_trigger: ".o_we_customize_panel .o_we_color_preview",
        content: markup(_t(`<b>Select</b> a Color Palette.`)),
        position: position,
        run: 'click',
        location: position === 'left' ? '#oe_snippets' : undefined,
    };
}

function changeColumnSize(position = "right") {
    return {
        trigger: `iframe .oe_overlay.o_draggable.o_we_overlay_sticky.oe_active .o_handle.e`,
        content: markup(_t("<b>Slide</b> this button to change the column size.")),
        position: position,
    };
}

function changeIcon(snippet, index = 0, position = "bottom") {
    return {
        trigger: `#wrapwrap .${snippet.id} i:eq(${index})`,
        extra_trigger: "body.editor_enable",
        content: markup(_t("<b>Double click on an icon</b> to change it with one of your choice.")),
        position: position,
        run: "dblclick",
    };
}

function changeImage(snippet, position = "bottom") {
    return {
        trigger: snippet.id ? `#wrapwrap .${snippet.id} img` : snippet,
        extra_trigger: "body.editor_enable",
        content: markup(_t("<b>Double click on an image</b> to change it with one of your choice.")),
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
        content: markup(_t("<b>Click</b> on this option to change the %s of the block.", optionTooltipLabel)),
        position: position,
        in_modal: false,
        run: "click",
    };
}

function selectNested(trigger, optionName, alt_trigger = null, optionTooltipLabel = '', position = "top", allowPalette = false) {
    const noPalette = allowPalette ? '' : '.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened))';
    const option_block = `${noPalette} we-customizeblock-option[class='snippet-option-${optionName}']`;
    return {
        trigger: trigger,
        content: markup(_t("<b>Select</b> a %s.", optionTooltipLabel)),
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
        trigger: `iframe .oe_overlay.o_draggable.o_we_overlay_sticky.oe_active .o_handle.${paddingDirection}`,
        content: markup(_t("<b>Slide</b> this button to change the %s padding", direction)),
        consumeEvent: 'mousedown',
        position: position,
    };
}

/**
 * Checks if an element is visible on the screen, i.e., not masked by another
 * element.
 * 
 * @param {String} elementSelector The selector of the element to be checked.
 * @returns {Object} The steps required to check if the element is visible.
 */
function checkIfVisibleOnScreen(elementSelector) {
    return {
        content: "Check if the element is visible on screen",
        trigger: `${elementSelector}`,
        run() {
            const boundingRect = this.$anchor[0].getBoundingClientRect();
            const centerX = boundingRect.left + boundingRect.width / 2;
            const centerY = boundingRect.top + boundingRect.height / 2;
            const iframeDocument = document.querySelector(".o_iframe").contentDocument;
            const el = iframeDocument.elementFromPoint(centerX, centerY);
            if (!this.$anchor[0].contains(el)) {
                console.error("The element is not visible on screen");
            }
        },
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
 * Click on the top right edit button and wait for the edit mode
 *
 * @param {string} position Where the purple arrow will show up
 */
function clickOnEditAndWaitEditMode(position = "bottom") {
    return [{
        content: markup(_t("<b>Click Edit</b> to start designing your homepage.")),
        trigger: ".o_menu_systray .o_edit_website_container a",
        position: position,
    }, {
        content: "Check that we are in edit mode",
        trigger: ".o_website_preview.editor_enable.editor_has_snippets",
        auto: true, // Checking step only for automated tests
        isCheck: true,
    }];
}

/**
 * Simple click on a snippet in the edition area
 * @param {*} snippet
 * @param {*} position
 */
function clickOnSnippet(snippet, position = "bottom") {
    const trigger = snippet.id ? `#wrapwrap .${snippet.id}` : snippet;
    return {
        trigger: `iframe ${trigger}`,
        extra_trigger: "body.editor_has_snippets",
        content: markup(_t("<b>Click on a snippet</b> to access its options menu.")),
        position: position,
        run: "click",
    };
}

function clickOnSave(position = "bottom", timeout) {
    return [{
        trigger: "div:not(.o_loading_dummy) > #oe_snippets button[data-action=\"save\"]:not([disabled])",
        // TODO this should not be needed but for now it better simulates what
        // an human does. By the time this was added, it's technically possible
        // to drag and drop a snippet then immediately click on save and have
        // some problem. Worst case probably is a traceback during the redirect
        // after save though so it's not that big of an issue. The problem will
        // of course be solved (or at least prevented in stable). More details
        // in related commit message.
        extra_trigger: "body:not(:has(.o_dialog)) #oe_snippets:not(:has(.o_we_already_dragging))",
        in_modal: false,
        content: markup(_t("Good job! It's time to <b>Save</b> your work.")),
        position: position,
        timeout: timeout,
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
        content: markup(_t("<b>Click on a text</b> to start editing it.")),
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
        content: markup(_t("Drag the <b>%s</b> building block and drop it at the bottom of the page.", snippet.name)),
        position: position,
        // Normally no main snippet can be dropped in the default footer but
        // targeting it allows to force "dropping at the end of the page".
        run: "drag_and_drop_native iframe #wrapwrap > footer",
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
        content: markup(_t(`<b>Click</b> on this header to configure it.`)),
        position: position,
        run: "click",
    };
}

function selectSnippetColumn(snippet, index = 0, position = "bottom") {
     return {
        trigger: `iframe #wrapwrap .${snippet.id} .row div[class*="col-lg-"]:eq(${index})`,
        content: markup(_t("<b>Click</b> on this column to access its options.")),
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
    let url = `/web#action=website.website_preview`;
    if (path) {
        url += `&path=${encodeURIComponent(path)}`;
    }
    if (edition) {
        url += '&enable_editor=1';
    }
    return url;
}

function clickOnExtraMenuItem(stepOptions, backend = false) {
    return Object.assign({}, {
        content: "Click on the extra menu dropdown toggle if it is there",
        trigger: `${backend ? "iframe" : ""} .top_menu`,
        run: function () {
            const extraMenuButton = this.$anchor[0].querySelector('.o_extra_menu_items a.nav-link');
            // Don't click on the extra menu button if it's already visible.
            if (extraMenuButton && !extraMenuButton.classList.contains("show")) {
                extraMenuButton.click();
            }
        },
    }, stepOptions);
}

/**
 * Registers a tour that will go in the website client action.
 *
 * @param {string} name The tour's name
 * @param {object} options The tour options
 * @param {string} options.url The page to edit
 * @param {boolean} [options.edition] If the tour starts in edit mode
 * @param {() => TourStep[]} steps The steps of the tour. Has to be a function to avoid direct interpolation of steps.
 */
function registerWebsitePreviewTour(name, options, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    return registry.category("web_tour.tours").add(name, {
        ...options,
        url: getClientActionUrl(options.url, !!options.edition),
        steps: () => {
            const tourSteps = [...steps()];
            // Note: for both non edit mode and edit mode, we set a high timeout for the
            // first step. Indeed loading both the backend and the frontend (in the
            // iframe) and potentially starting the edit mode can take a long time in
            // automatic tests. We'll try and decrease the need for this high timeout
            // of course.
            if (options.edition) {
                tourSteps.unshift({
                    content: "Wait for the edit mode to be started",
                    trigger: ".o_website_preview.editor_enable.editor_has_snippets",
                    timeout: 30000,
                    auto: true,
                    run: () => {}, // It's a check
                });
            } else {
                tourSteps[0].timeout = 20000;
            }
            return tourSteps;
        },
    });
}

function registerThemeHomepageTour(name, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    return registerWebsitePreviewTour(name, {
        url: '/',
        sequence: 50,
        saveAs: "homepage",
        },
        () => [
            ...clickOnEditAndWaitEditMode(),
            ...prepend_trigger(
                steps().concat(clickOnSave()),
                ".o_website_preview[data-view-xmlid='website.homepage'] "
            ),
    ]);
}

function registerBackendAndFrontendTour(name, options, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    if (window.location.pathname === '/web') {
        return registerWebsitePreviewTour(name, options, () => {
            const newSteps = [];
            for (const step of steps()) {
                const newStep = Object.assign({}, step);
                newStep.trigger = `iframe ${step.trigger}`;
                if (step.extra_trigger) {
                    newStep.extra_trigger = `iframe ${step.extra_trigger}`;
                }
                newSteps.push(newStep);
            }
            return newSteps;
        });
    }

    return registry.category("web_tour.tours").add(name, {
        url: options.url,
        steps: () => {
            return steps();
        },
    });
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
        `we-select[data-name="${widgetName}"] we-button:contains("${elementName}"), ` +
        `we-select[data-name="${widgetName}"] we-button[data-select-label="${elementName}"]`));
    steps.push({
        content: "Check we-select is set",
        trigger: `we-select[data-name=${widgetName}]:contains(${elementName})`,
        async run() {
            // TODO: remove this delay when macro.js has been fixed.
            // This additionnal line fix an underterministic error.
            // When we-select is used twice a row too fast,
            // the second we-select may not open.
            // The first toggle is open, we click on it and almost
            // at the same time, we click on the second one.
            // The problem comes from macro.js which does not give
            // the DOM time to be stable before looking for the trigger.
            // We add a delay to let the mutations take place and
            // therefore wait for the DOM to stabilize.
            await new Promise((resolve) => setTimeout(resolve, 300));
        }
    });
    return steps;
}

/**
 * Switches to a different website by clicking on the website switcher.
 *
 * @param {number} websiteId - The ID of the website to switch to.
 * @param {string} websiteName - The name of the website to switch to.
 * @returns {Array} - The steps required to perform the website switch.
 */
function switchWebsite(websiteId, websiteName) {
    return [{
        content: `Click on the website switch to switch to website '${websiteName}'`,
        trigger: '.o_website_switcher_container button',
    }, {
        content: `Switch to website '${websiteName}'`,
        extra_trigger: `iframe html:not([data-website-id="${websiteId}"])`,
        trigger: `.o_website_switcher_container .dropdown-item[data-website-id=${websiteId}]:contains("${websiteName}")`,
    }, {
        content: "Wait for the iframe to be loaded",
        // The page reload generates assets for the new website, it may take
        // some time
        timeout: 20000,
        trigger: `iframe html[data-website-id="${websiteId}"]`,
        isCheck: true,
    }];
}

/**
* Switches to a different website by clicking on the website switcher.
* This function can only be used during test tours as it requires
* specific cookies to properly function.
*
* @param {string} websiteName - The name of the website to switch to.
* @returns {Array} - The steps required to perform the website switch.
*/
function testSwitchWebsite(websiteName) {
   const websiteIdMapping = JSON.parse(cookie.get('websiteIdMapping') || '{}');
   const websiteId = websiteIdMapping[websiteName];
   return switchWebsite(websiteId, websiteName)
}

/**
 * Toggles the mobile preview on or off.
 *
 * @param {Boolean} toggleOn true to toggle the mobile preview on, false to
 *     toggle it off.
 * @returns {Array}
 */
function toggleMobilePreview(toggleOn) {
    const onOrOff = toggleOn ? "on" : "off";
    const mobileOnSelector = ".o_is_mobile";
    const mobileOffSelector = ":not(.o_is_mobile)";
    return [{
        content: `Toggle the mobile preview ${onOrOff}`,
        trigger: ".o_we_website_top_actions [data-action='mobile']",
        extra_trigger: `iframe #wrapwrap${toggleOn ? mobileOffSelector : mobileOnSelector}`,
    }, {
        content: `Check that the mobile preview is ${onOrOff}`,
        trigger: `iframe #wrapwrap${toggleOn ? mobileOnSelector : mobileOffSelector}`,
        isCheck: true,
    }];
}

export default {
    addMedia,
    assertCssVariable,
    assertPathName,
    changeBackground,
    changeBackgroundColor,
    changeColumnSize,
    changeIcon,
    changeImage,
    changeOption,
    changePaddingSize,
    checkIfVisibleOnScreen,
    clickOnEditAndWaitEditMode,
    clickOnElement,
    clickOnExtraMenuItem,
    clickOnSave,
    clickOnSnippet,
    clickOnText,
    dragNDrop,
    getClientActionUrl,
    goBackToBlocks,
    goToTheme,
    registerBackendAndFrontendTour,
    registerThemeHomepageTour,
    registerWebsitePreviewTour,
    selectColorPalette,
    selectElementInWeSelectWidget,
    selectHeader,
    selectNested,
    selectSnippetColumn,
    switchWebsite,
    testSwitchWebsite,
    toggleMobilePreview,
};
