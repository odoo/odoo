/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";
import { omit } from "@web/core/utils/objects";

export function addMedia(position = "right") {
    return {
        trigger: `.modal-content footer .btn-primary`,
        content: markup(_t("<b>Add</b> the selected image.")),
        tooltipPosition: position,
        run: "click",
    };
}
export function assertCssVariable(variableName, variableValue, trigger = ':iframe body') {
    return {
        isActive: ["auto"],
        content: `Check CSS variable ${variableName}=${variableValue}`,
        trigger: trigger,
        run() {
            const styleValue = getComputedStyle(this.anchor).getPropertyValue(variableName);
            if ((styleValue && styleValue.trim().replace(/["']/g, '')) !== variableValue.trim().replace(/["']/g, '')) {
                throw new Error(`Failed precondition: ${variableName}=${styleValue} (should be ${variableValue})`);
            }
        },
    };
}
export function assertPathName(pathName, trigger) {
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

export function changeBackground(snippet, position = "bottom") {
    return [
        {
            trigger: ".o_we_customize_panel .o_we_bg_success",
        content: markup(_t("<b>Customize</b> any block through this menu. Try to change the background image of this block.")),
            tooltipPosition: position,
            run: "click",
        },
    ];
}

export function changeBackgroundColor(position = "bottom") {
    return {
        trigger: ".o_we_customize_panel .o_we_color_preview",
        content: markup(_t("<b>Customize</b> any block through this menu. Try to change the background color of this block.")),
        tooltipPosition: position,
        run: "click",
    };
}

export function selectColorPalette(position = "left") {
    return {
        trigger:
            ".o_we_customize_panel .o_we_so_color_palette we-selection-items, .o_we_customize_panel .o_we_color_preview",
        content: markup(_t(`<b>Select</b> a Color Palette.`)),
        tooltipPosition: position,
        run: 'click',
    };
}

export function changeColumnSize(position = "right") {
    return {
        trigger: `:iframe .oe_overlay.o_draggable.o_we_overlay_sticky.oe_active .o_handle.e`,
        content: markup(_t("<b>Slide</b> this button to change the column size.")),
        tooltipPosition: position,
        run: "click",
    };
}

export function changeImage(snippet, position = "bottom") {
    return [
        {
            trigger: "body.editor_enable",
        },
        {
            trigger: snippet.id ? `#wrapwrap .${snippet.id} img` : snippet,
        content: markup(_t("<b>Double click on an image</b> to change it with one of your choice.")),
            tooltipPosition: position,
            run: "dblclick",
        },
    ];
}

/**
    wTourUtils.changeOption('HeaderTemplate', '[data-name="header_alignment_opt"]', _t('alignment')),
    By default, prevents the step from being active if a palette is opened.
    Set allowPalette to true to select options within a palette.
*/
export function changeOption(optionName, weName = '', optionTooltipLabel = '', position = "bottom", allowPalette = false) {
    const noPalette = allowPalette ? '' : '.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened))';
    const option_block = `${noPalette} we-customizeblock-option[class='snippet-option-${optionName}']`;
    return {
        trigger: `${option_block} ${weName}, ${option_block} [title='${weName}']`,
        content: markup(_t("<b>Click</b> on this option to change the %s of the block.", optionTooltipLabel)),
        tooltipPosition: position,
        run: "click",
    };
}

export function selectNested(trigger, optionName, altTrigger = null, optionTooltipLabel = '', position = "top", allowPalette = false) {
    const noPalette = allowPalette ? '' : '.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened))';
    const option_block = `${noPalette} we-customizeblock-option[class='snippet-option-${optionName}']`;
    return {
        trigger: trigger + (altTrigger ? `, ${option_block} ${altTrigger}` : ""),
        content: markup(_t("<b>Select</b> a %s.", optionTooltipLabel)),
        tooltipPosition: position,
        run: 'click',
    };
}

export function changePaddingSize(direction) {
    let paddingDirection = "n";
    let position = "top";
    if (direction === "bottom") {
        paddingDirection = "s";
        position = "bottom";
    }
    return {
        trigger: `:iframe .oe_overlay.o_draggable.o_we_overlay_sticky.oe_active .o_handle.${paddingDirection}`,
        content: markup(_t("<b>Slide</b> this button to change the %s padding", direction)),
        tooltipPosition: position,
        run: "click",
    };
}

/**
 * Checks if an element is visible on the screen, i.e., not masked by another
 * element.
 *
 * @param {String} elementSelector The selector of the element to be checked.
 * @returns {Object} The steps required to check if the element is visible.
 */
export function checkIfVisibleOnScreen(elementSelector) {
    return {
        content: "Check if the element is visible on screen",
        trigger: `${elementSelector}`,
        run() {
            const boundingRect = this.anchor.getBoundingClientRect();
            const centerX = boundingRect.left + boundingRect.width / 2;
            const centerY = boundingRect.top + boundingRect.height / 2;
            const iframeDocument = document.querySelector(".o_iframe").contentDocument;
            const el = iframeDocument.elementFromPoint(centerX, centerY);
            if (!this.anchor.contains(el)) {
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
export function clickOnElement(elementName, selector) {
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
export function clickOnEditAndWaitEditMode(position = "bottom") {
    return [{
        content: markup(_t("<b>Click Edit</b> to start designing your homepage.")),
        trigger: ".o_menu_systray .o_edit_website_container a",
        tooltipPosition: position,
        run: "click",
    }, {
        isActive: ["auto"], // Checking step only for automated tests
        content: "Check that we are in edit mode",
        trigger: ".o_website_preview.editor_enable.editor_has_snippets",
    }];
}

/**
 * Click on the top right edit dropdown, then click on the edit dropdown item
 * and wait for the edit mode
 *
 * @param {string} position Where the purple arrow will show up
 */
export function clickOnEditAndWaitEditModeInTranslatedPage(position = "bottom") {
    return [{
        content: markup(_t("<b>Click Edit</b> dropdown")),
        trigger: ".o_edit_website_container button",
        tooltipPosition: position,
        run: "click",
    }, {
        content: markup(_t("<b>Click Edit</b> to start designing your homepage.")),
        trigger: ".o_edit_website_dropdown_item",
        tooltipPosition: position,
        run: "click",
    }, {
        isActive: ["auto"], // Checking step only for automated tests
        content: "Check that we are in edit mode",
        trigger: ".o_website_preview.editor_enable.editor_has_snippets",
    }];
}

/**
 * Simple click on a snippet in the edition area
 * @param {*} snippet
 * @param {*} position
 */
export function clickOnSnippet(snippet, position = "bottom") {
    const trigger = snippet.id ? `#wrapwrap .${snippet.id}` : snippet;
    return [
        {
            trigger: "body.editor_has_snippets",
            noPrepend: true,
        },
        {
            trigger: `:iframe ${trigger}`,
        content: markup(_t("<b>Click on a snippet</b> to access its options menu.")),
            tooltipPosition: position,
            run: "click",
        },
    ];
}

export function clickOnSave(position = "bottom", timeout) {
    return [
        {
            trigger: "#oe_snippets:not(:has(.o_we_ongoing_insertion))",
        },
        {
            trigger: "body:not(:has(.o_dialog))",
            noPrepend: true,
        },
        {
            trigger:
                'div:not(.o_loading_dummy) > #oe_snippets button[data-action="save"]:not([disabled])',
            // TODO this should not be needed but for now it better simulates what
            // an human does. By the time this was added, it's technically possible
            // to drag and drop a snippet then immediately click on save and have
            // some problem. Worst case probably is a traceback during the redirect
            // after save though so it's not that big of an issue. The problem will
            // of course be solved (or at least prevented in stable). More details
            // in related commit message.
        content: markup(_t("Good job! It's time to <b>Save</b> your work.")),
            tooltipPosition: position,
            timeout: timeout,
            run: "click",
        },
        {
            isActive: ["auto"], // Just making sure save is finished in automatic tests
            trigger: ":iframe body:not(.editor_enable)",
            noPrepend: true,
            timeout: timeout,
        },
    ];
}

/**
 * Click on a snippet's text to modify its content
 * @param {*} snippet
 * @param {*} element Target the element which should be rewrite
 * @param {*} position
 */
export function clickOnText(snippet, element, position = "bottom") {
    return [
        {
            trigger: ":iframe body.editor_enable",
        },
        {
            trigger: snippet.id ? `:iframe #wrapwrap .${snippet.id} ${element}` : snippet,
        content: markup(_t("<b>Click on a text</b> to start editing it.")),
            tooltipPosition: position,
            run: "click",
        },
    ];
}

/**
 * Selects a category or an inner snippet from the snippets menu and insert it
 * in the page.
 * @param {*} snippet contain the id and the name of the targeted snippet. If it
 * contains a group it means that the snippet is shown in the "add snippets"
 * dialog.
 * @param {*} position Where the purple arrow will show up
 */
export function insertSnippet(snippet, position = "bottom") {
    const blockEl = snippet.groupName || snippet.name;
    const insertSnippetSteps = [{
        trigger: ".o_website_preview.editor_enable.editor_has_snippets",
        noPrepend: true,
    }];
    if (snippet.groupName) {
        insertSnippetSteps.push({
            content: markup(_t("Click on the <b>%s</b> category.", blockEl)),
            trigger: `#oe_snippets .oe_snippet[name="${blockEl}"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)`,
            tooltipPosition: position,
            run: "click",
        },
        {
            content: markup(_t("Click on the <b>%s</b> building block.", snippet.name)),
            // FIXME `:not(.d-none)` should obviously not be needed but it seems
            // currently needed when using a tour in user/interactive mode.
            trigger: `:iframe .o_snippet_preview_wrap[data-snippet-id="${snippet.id}"]:not(.d-none)`,
            noPrepend: true,
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: `#oe_snippets .oe_snippet[name="${blockEl}"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)`,
        });
    } else {
        insertSnippetSteps.push({
            content: markup(_t("Drag the <b>%s</b> block and drop it at the bottom of the page.", blockEl)),
            trigger: `#oe_snippets .oe_snippet[name="${blockEl}"].o_we_draggable .oe_snippet_thumbnail:not(.o_we_ongoing_insertion)`,
            tooltipPosition: position,
            run: "drag_and_drop :iframe #wrapwrap > footer",
        });
    }
    return insertSnippetSteps;
}

export function goBackToBlocks(position = "bottom") {
    return {
        trigger: '.o_we_add_snippet_btn',
        content: _t("Click here to go back to block tab."),
        tooltipPosition: position,
        run: "click",
    };
}

export function goToTheme(position = "bottom") {
    return [
        {
            trigger: "#oe_snippets.o_loaded",
        },
        {
            trigger: ".o_we_customize_theme_btn",
            content: _t("Go to the Theme tab"),
            tooltipPosition: position,
            run: "click",
        },
    ];
}

export function selectHeader(position = "bottom") {
    return {
        trigger: `:iframe header#top`,
        content: markup(_t(`<b>Click</b> on this header to configure it.`)),
        tooltipPosition: position,
        run: "click",
    };
}

export function selectSnippetColumn(snippet, index = 0, position = "bottom") {
     return {
        trigger: `:iframe #wrapwrap .${snippet.id} .row div[class*="col-lg-"]:eq(${index})`,
        content: markup(_t("<b>Click</b> on this column to access its options.")),
         tooltipPosition: position,
        run: "click",
     };
}

export function prepend_trigger(steps, prepend_text='') {
    for (const step of steps) {
        if (!step.noPrepend && prepend_text) {
            step.trigger = prepend_text + step.trigger;
        }
    }
    return steps;
}

export function getClientActionUrl(path, edition) {
    let url = `/odoo/action-website.website_preview`;
    if (path) {
        url += `?path=${encodeURIComponent(path)}`;
    }
    if (edition) {
        url += `${path ? '&' : '?'}enable_editor=1`;
    }
    return url;
}

export function clickOnExtraMenuItem(stepOptions, backend = false) {
    return Object.assign({
        content: "Click on the extra menu dropdown toggle if it is there",
        trigger: `${backend ? ":iframe" : ""} .top_menu`,
        async run(actions) {
            const extraMenuButton = this.anchor.querySelector(".o_extra_menu_items a.nav-link");
            // Don't click on the extra menu button if it's already visible.
            if (extraMenuButton && !extraMenuButton.classList.contains("show")) {
                await actions.click(extraMenuButton);
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
export function registerWebsitePreviewTour(name, options, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    return registry.category("web_tour.tours").add(name, {
        ...omit(options, "edition"),
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
                    isActive: ["auto"],
                    content: "Wait for the edit mode to be started",
                    trigger: ".o_website_preview.editor_enable.editor_has_snippets",
                    timeout: 30000,
                });
            } else {
                tourSteps[0].timeout = 20000;
            }
            return tourSteps.map((step) => {
                delete step.noPrepend;
                return step;
            });
        },
    });
}

export function registerThemeHomepageTour(name, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    return registerWebsitePreviewTour(name, {
        url: '/',
        saveAs: "homepage", // disable manual mode for theme homepage tours - FIXME
        },
        () => [
            ...clickOnEditAndWaitEditMode(),
            ...prepend_trigger(
                steps().concat(clickOnSave()),
                ".o_website_preview[data-view-xmlid='website.homepage'] "
            ),
    ]);
}

export function registerBackendAndFrontendTour(name, options, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    if (window.location.pathname === '/odoo') {
        return registerWebsitePreviewTour(name, options, () => {
            const newSteps = [];
            for (const step of steps()) {
                const newStep = Object.assign({}, step);
                newStep.trigger = `:iframe ${step.trigger}`;
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
export function selectElementInWeSelectWidget(widgetName, elementName, searchNeeded = false) {
    const steps = [clickOnElement(`${widgetName} toggler`, `we-select[data-name=${widgetName}] we-toggler`)];

    if (searchNeeded) {
        steps.push({
            content: `Inputing ${elementName} in m2o widget search`,
            trigger: `we-select[data-name=${widgetName}] div.o_we_m2o_search input`,
            run: `edit ${elementName}`,
        });
    }
    steps.push(clickOnElement(`${elementName} in the ${widgetName} widget`,
        `we-select[data-name="${widgetName}"] we-button:contains("${elementName}"), ` +
        `we-select[data-name="${widgetName}"] we-button[data-select-label="${elementName}"]`));
    return steps;
}

/**
 * Switches to a different website by clicking on the website switcher.
 *
 * @param {number} websiteId - The ID of the website to switch to.
 * @param {string} websiteName - The name of the website to switch to.
 * @returns {Array} - The steps required to perform the website switch.
 */
export function switchWebsite(websiteId, websiteName) {
    return [{
        content: `Click on the website switch to switch to website '${websiteName}'`,
        trigger: '.o_website_switcher_container button',
        run: "click",
    },
    {
        trigger: `:iframe html:not([data-website-id="${websiteId}"])`,
    },
    {
        content: `Switch to website '${websiteName}'`,
        trigger: `.o-dropdown--menu .dropdown-item:contains("${websiteName}")`,
        run: "click",
    }, {
        content: "Wait for the iframe to be loaded",
        // The page reload generates assets for the new website, it may take
        // some time
        timeout: 20000,
        trigger: `:iframe html[data-website-id="${websiteId}"]`,
    }];
}

/**
 * Toggles the mobile preview on or off.
 *
 * @param {Boolean} toggleOn true to toggle the mobile preview on, false to
 *     toggle it off.
 * @returns {Array}
 */
export function toggleMobilePreview(toggleOn) {
    const onOrOff = toggleOn ? "on" : "off";
    const mobileOnSelector = ".o_is_mobile";
    const mobileOffSelector = ":not(.o_is_mobile)";
    return [
        {
            trigger: `:iframe html${toggleOn ? mobileOffSelector : mobileOnSelector}`,
        },
        {
            content: `Toggle the mobile preview ${onOrOff}`,
            trigger: ".o_we_website_top_actions [data-action='mobile']",
            run: "click",
        },
        {
            content: `Check that the mobile preview is ${onOrOff}`,
            trigger: `:iframe html${toggleOn ? mobileOnSelector : mobileOffSelector}`,
        },
    ];
}
