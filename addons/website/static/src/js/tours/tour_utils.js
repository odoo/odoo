import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";

import { markup } from "@odoo/owl";
import { omit } from "@web/core/utils/objects";
import { stepUtils } from "@web_tour/tour_utils";

export function addMedia(position = "right") {
    return {
        trigger: `.modal-content footer .btn-primary`,
        content: markup(_t("<b>Add</b> the selected image.")),
        tooltipPosition: position,
        run: "click",
    };
}
export function assertCssVariable(variableName, variableValue, trigger = ":iframe body") {
    return {
        isActive: ["auto"],
        content: `Check CSS variable ${variableName}=${variableValue}`,
        trigger: trigger,
        run() {
            const styleValue = getComputedStyle(this.anchor).getPropertyValue(variableName);
            if (
                (styleValue && styleValue.trim().replace(/["']/g, "")) !==
                variableValue.trim().replace(/["']/g, "")
            ) {
                throw new Error(
                    `Failed precondition: ${variableName}=${styleValue} (should be ${variableValue})`
                );
            }
        },
    };
}
export function assertPathName(pathname, trigger) {
    return {
        content: `Check if we have been redirected to ${pathname}`,
        trigger: trigger,
        async run() {
            await new Promise((resolve) => {
                let elapsedTime = 0;
                const intervalTime = 100;
                const interval = setInterval(() => {
                    if (window.location.pathname.startsWith(pathname)) {
                        clearInterval(interval);
                        resolve();
                    }
                    elapsedTime += intervalTime;
                    if (elapsedTime >= 5000) {
                        clearInterval(interval);
                        console.error(`The pathname ${pathname} has not been found`);
                    }
                }, intervalTime);
            });
        },
    };
}

export function changeBackground(snippet, position = "bottom") {
    return [
        {
            trigger: `.o_customize_tab button[data-action-id="replaceBgImage"]`,
            content: markup(_t("<b>Customize</b> any block through this menu. Try to change the background image of this block.")),
            tooltipPosition: position,
            run: "click",
        },
    ];
}

export function changeBackgroundColor(position = "bottom") {
    return {
        trigger: ".o_customize_tab .o_we_color_preview",
        content: markup(_t("<b>Customize</b> any block through this menu. Try to change the background color of this block.")),
        tooltipPosition: position,
        run: "click",
    };
}

// TODO: RAHG: This function's trigger is same as above. need to be changed
// to avoid duplication
export function selectColorPalette(position = "left") {
    return {
        trigger:
            ".o_customize_tab .o_we_color_preview",
        content: markup(_t(`<b>Select</b> a Color Palette.`)),
        tooltipPosition: position,
        run: 'click',
    };
}

export function changeColumnSize(position = "right") {
    return {
        trigger: `.oe_overlay.oe_active .o_handles .o_handle:not(.readonly)`,
        content: markup(_t("<b>Slide</b> this button to change the column size.")),
        tooltipPosition: position,
        run: "click",
    };
}

export function changeImage(snippet, position = "bottom") {
    return [
        {
            trigger: ".o_builder_sidebar_open",
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
    const noPalette = allowPalette ? "" : !document.querySelector(".o_popover .o_font_color_selector") && ".o_customize_tab";
    const option_block = `${noPalette} [data-container-title='${optionName}']`;
    return {
        trigger: `${option_block} ${weName}, ${option_block} [data-action-id="${weName}"]`,
        content: markup(_t("<b>Click</b> on this option to change the %s of the block.", optionTooltipLabel)),
        tooltipPosition: position,
        run: "click",
    };
}

/*
 * This function is used when the desired UI control is embedded inside popover
 * (e.g., a dropdown that appears only after clicking a toggle).
 *
 * It constructs two steps:
 *   1. Clicks the dropdown toggle or control to open the popover.
 *   2. Clicks the target element (option) inside the popover.
 *
 * Note: This function assumes that the popover content is available and render
 *       immediately after the first click.
 *
 * @param {string} blockName - The name of the block (e.g., "Text - Image").
 * @param {string} optionName - The name of the option (e.g., "Visibility").
 * @param {string} elementName - The name of the element to be clicked inside
 *                               the popover (e.g., "Conditionally").
 * @param {Boolean} searchNeeded - If the widget is a m2o widget and a search is needed.
 *
 * Example:
 *      ...changeOptionInPopover("Text - Image", "Visibility", "Conditionally")
 */
export function changeOptionInPopover(blockName, optionName, elementName, searchNeeded = false) {
    const steps = [changeOption(blockName, `[data-label='${optionName}'] .dropdown-toggle`)];

    if (searchNeeded) {
        steps.push({
            content: `Inputing ${elementName} in toogle option search`,
            trigger: `.o_popover input`,
            run: `edit ${elementName}`,
        });
    }

    steps.push(
        clickOnElement(
            `${elementName} in the ${optionName} option`,
            `.o_popover div.o-dropdown-item:contains("${elementName}"), .o_popover span.o-dropdown-item:contains("${elementName}"), .o_popover ${elementName}`
        )
    );
    return steps;
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
        trigger: `.oe_overlay.oe_active .o_handle.${paddingDirection}`,
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
            const iframeDocument = document.querySelector(
                ".o_website_preview iframe"
            ).contentDocument;
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
        trigger: "body .o_menu_systray button:contains('Edit')",
        tooltipPosition: position,
        run: "click",
    }, {
        content: "Check that we are in edit mode",
        trigger: ".o_builder_sidebar_open",
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
        trigger: "body .o_menu_systray button:contains('Edit')",
        tooltipPosition: position,
        run: "click",
    }, {
        content: markup(_t("<b>Click Edit</b> to start designing your homepage.")),
        trigger: ".o_edit_website_dropdown_item",
        tooltipPosition: position,
        run: "click",
    }, {
        content: "Check that we are in edit mode",
        trigger: ".o_builder_sidebar_open",
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
            trigger: ".o-website-builder_sidebar",
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

export function clickOnSave(position = "bottom", timeout = 50000) {
    return [
        {
            trigger: ".o-snippets-menu:not(:has(.o_we_ongoing_insertion))",
        },
        {
            trigger: "body:not(:has(.o_dialog))",
            noPrepend: true,
        },
        {
            trigger: "button[data-action=save]:enabled:contains(save)",
        content: markup(_t("Good job! It's time to <b>Save</b> your work.")),
            tooltipPosition: position,
            run: "click",
            timeout,
        },
        {
            trigger: "body:not(.o_builder_open)",
            noPrepend: true,
            timeout,
        },
        stepUtils.waitIframeIsReady(),
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
            trigger: ":iframe body .odoo-editor-editable",
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
export function insertSnippet(snippet, { position = "bottom", ignoreLoading = false } = {}) {
    const blockEl = snippet.groupName || snippet.name;
    const insertSnippetSteps = [{
        trigger: ".o_builder_sidebar_open",
        noPrepend: true,
    }];
    const snippetIDSelector = snippet.id ? `[data-snippet-id="${snippet.id}"]` : `[data-snippet-id^="${snippet.customID}_"]`;
    if (snippet.groupName) {
        insertSnippetSteps.push({
            content: markup(_t("Click on the <b>%s</b> category.", blockEl)),
            trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="${blockEl}"].o_draggable .o_snippet_thumbnail_area`,
            tooltipPosition: position,
            run: "click",
        },
        {
            content: markup(_t("Click on the <b>%s</b> building block.", snippet.name)),
            // FIXME `:not(.d-none)` should obviously not be needed but it seems
            // currently needed when using a tour in user/interactive mode.
            trigger: `.modal .show:iframe .o_snippet_preview_wrap${snippetIDSelector}:not(.d-none)`,
            noPrepend: true,
            tooltipPosition: "top",
            run: "click",
        });
    } else {
        insertSnippetSteps.push({
            content: markup(_t("Drag the <b>%s</b> block and drop it at the bottom of the page.", blockEl)),
            trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_content .o_snippet[name="${blockEl}"].o_draggable .o_snippet_thumbnail`,
            tooltipPosition: position,
            run: "drag_and_drop :iframe #wrapwrap > footer",
        });
    }

    if (!ignoreLoading) {
        insertSnippetSteps.push({
            trigger: ":iframe:not(:has(.o_loading_screen))",
        });
    }

    return insertSnippetSteps;
}

export function goBackToBlocks(position = "bottom") {
    return {
        trigger: "button[data-name='blocks']",
        content: _t("Click here to go back to block tab."),
        tooltipPosition: position,
        run: "click",
    };
}

export function goToTheme(position = "bottom") {
    return [
        {
            trigger: ".o-website-builder_sidebar",
        },
        {
            trigger: "button[data-name='theme']",
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
            // Note: the button might not exist (it only appear if there is many menu items)
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
    registry.category("web_tour.tours").remove(name);
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
                    content: "Wait for the edit mode to be started",
                    trigger: ".o_builder_sidebar_open",
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
    return registerWebsitePreviewTour(
        name,
        {
            url: "/",
        },
        () => [
            ...clickOnEditAndWaitEditMode(),
            ...prepend_trigger(
                steps().concat(clickOnSave())),
        ]
    );
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
        trigger: `.o-dropdown--menu .dropdown-item[data-website-id="${websiteId}"]:contains("${websiteName}")`,
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
* Switches to a different website by clicking on the website switcher.
* This function can only be used during test tours as it requires
* specific cookies to properly function.
*
* @param {string} websiteName - The name of the website to switch to.
* @returns {Array} - The steps required to perform the website switch.
*/
export function testSwitchWebsite(websiteName) {
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
export function toggleMobilePreview(toggleOn) {
    const onOrOff = toggleOn ? "on" : "off";
    const mobileOnSelector = ".o_is_mobile";
    const mobileOffSelector = ":not(.o_is_mobile)";
    return [
        {
            trigger: `div.o_website_preview${toggleOn ? mobileOffSelector : mobileOnSelector}`,
        },
        {
            content: `Toggle the mobile preview ${onOrOff}`,
            trigger: ".o-snippets-top-actions [data-action='mobile']",
            run: "click",
        },
        {
            content: `Check that the mobile preview is ${onOrOff}`,
            trigger: `div.o_website_preview${toggleOn ? mobileOnSelector : mobileOffSelector}`,
        },
    ];
}

/**
 * Opens the link popup for the specified link element.
 *
 * @param {string} triggerSelector - Selector for the link element.
 * @param {string} [linkName=""] - Name of the link.
 * @param {number} [focusNodeIndex=0] - Index of the child node to focus inside
 *                                      the link element.
 * @returns {TourStep[]} The tour steps that opens the link popup.
 */
export function openLinkPopup(
    triggerSelector,
    linkName = "",
    focusNodeIndex = 0,
    triggerClick = false
) {
    return [
        {
            content: `Open '${linkName}' link popup`,
            trigger: triggerSelector,
            async run(actions) {
                if (triggerClick) {
                    actions.click();
                }
                const el = this.anchor;
                const sel = el.ownerDocument.getSelection();
                sel.collapse(el.childNodes[focusNodeIndex], 1);
                el.focus();
            },
        },
        {
            content: "Check if the link popover opened",
            trigger: ".o-we-linkpopover",
        },
    ];
}

/**
 * Selects all the text of an element.
 * @param {*} elementName
 * @param {*} selector
 */
export function selectFullText(elementName, selector) {
    return {
        content: `Select all the text of the ${elementName}`,
        trigger: `:iframe ${selector}`,
        async run(actions) {
            await actions.click();
            const range = document.createRange();
            const selection = this.anchor.ownerDocument.getSelection();
            range.selectNodeContents(this.anchor);
            selection.removeAllRanges();
            selection.addRange(range);
        },
    };
}

/**
 * Click button from the toolbar, if expand is true, it will
 * first expand the toolbar.
 * @param {string} elementName
 * @param {string} selector
 * @param {string} button
 * @param {boolean} expand - Whether to expand the toolbar for more buttons.
 * @returns {Array} The steps to click the toolbar button.
 */
export function clickToolbarButton(elementName, selector, button, expand = false) {
    const steps = [
        selectFullText(`${elementName}`, selector),
        {
            content: `Click on the ${button} from toolbar`,
            trigger: `.o-we-toolbar button[title="${button}"]`,
            run: "click",
        },
    ];
    if (expand) {
        steps.splice(1, 0, {
            content: "Expand the toolbar for more buttons",
            trigger: ".o-we-toolbar button[name='expand_toolbar']",
            run: "click",
        });
    }
    return steps;
}
