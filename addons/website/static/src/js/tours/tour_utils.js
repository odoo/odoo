import { registry } from "@web/core/registry";
import { cookie } from "@web/core/browser/cookie";

import { omit } from "@web/core/utils/objects";
import { stepUtils } from "@web_tour/tour_utils";

export function addMedia() {
    return {
        trigger: `.modal-content footer .btn-primary`,
        content: "Add the selected image.",
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

export function changeBackground() {
    return [
        {
            trigger: `.o_customize_tab button[data-action-id="replaceBgImage"]`,
            content:
                "Customize any block through this menu. Try to change the background image of this block.",
            run: "click",
        },
    ];
}

export function changeBackgroundColor() {
    return {
        trigger: ".o_customize_tab .o_we_color_preview",
        content:
            "Customize any block through this menu. Try to change the background color of this block.",
        run: "click",
    };
}

export function changeImage(snippet) {
    return [
        {
            trigger: ".o_builder_sidebar_open",
        },
        {
            trigger: snippet.id ? `#wrapwrap .${snippet.id} img` : snippet,
            content: "Double click on an image to change it with one of your choice.",
            run: "dblclick",
        },
    ];
}

/**
    wTourUtils.changeOption('HeaderTemplate', '[data-name="header_alignment_opt"]', _t('alignment')),
    By default, prevents the step from being active if a palette is opened.
    Set allowPalette to true to select options within a palette.
*/
export function changeOption(
    blockName,
    actionId = "",
    optionTooltipLabel = "",
    allowPalette = false
) {
    const noPalette = allowPalette
        ? ""
        : !document.querySelector(".o_popover .o_font_color_selector") &&
          ".o-tab-content > [role='tabpanel']";
    const option_block = `${noPalette} [data-container-title='${blockName}']`;
    return {
        trigger: `${option_block} ${actionId}, ${option_block} [data-action-id="${actionId}"]`,
        content: `Click on this option to change the ${optionTooltipLabel} of the block.`,
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
 *
 * Example:
 *      ...changeOptionInPopover("Text - Image", "Visibility", "Conditionally")
 */
export function changeOptionInPopover(blockName, optionName, elementName) {
    const itemSelector = [
        `.o_popover .o-dropdown-item[title="${elementName}"]`,
        `.o_popover .o-dropdown-item:contains(${elementName})`,
    ].join(", ");
    return [
        changeOption(blockName, `[data-label='${optionName}'] .dropdown-toggle`),
        {
            content: `Check if "${elementName}" option is shown. If not, search for it.`,
            trigger: ".o_popover .o-dropdown-item",
            async run({ waitFor, edit }) {
                let item = await waitFor(itemSelector).catch(() => false);
                if (!item) {
                    const popoverInput = await waitFor(".o_popover input").catch(() => false);
                    if (popoverInput) {
                        await edit(elementName, ".o_popover input");
                    }
                }
                item = await waitFor(itemSelector).catch(() => false);
                if (!item) {
                    console.error(`${itemSelector} not found after edit`);
                }
            },
        },
        clickOnElement(`${elementName} in the ${optionName} option`, itemSelector),
    ];
}

export function selectNested(
    trigger,
    optionName,
    altTrigger = null,
    optionTooltipLabel = "",
    position = "top",
    allowPalette = false
) {
    const noPalette = allowPalette
        ? ""
        : ".o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened))";
    const option_block = `${noPalette} we-customizeblock-option[class='snippet-option-${optionName}']`;
    return {
        trigger: trigger + (altTrigger ? `, ${option_block} ${altTrigger}` : ""),
        content: `Select a ${optionTooltipLabel}.`,
        run: "click",
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
        content: `Slide this button to change the ${direction} padding`,
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
        run: "click",
    };
}

/**
 * Click on the top right edit button and wait for the edit mode
 *
 * @param {string} position Where the purple arrow will show up
 */
export function clickOnEditAndWaitEditMode() {
    return [
        {
            content: "Click Edit to start designing your homepage.",
            trigger:
                "body:has(:iframe body[is-ready=true]) .o_menu_systray .o_menu_systray_item.o_edit_website_container button",
            run: "click",
        },
        {
            content: "Check that we are in edit mode",
            trigger: ".o_builder_sidebar_open",
        },
    ];
}

/**
 * Click on the top right edit dropdown, then click on the edit dropdown item
 * and wait for the edit mode
 *
 * @param {string} position Where the purple arrow will show up
 */
export function clickOnEditAndWaitEditModeInTranslatedPage() {
    return [
        {
            content: "Click Edit dropdown",
            trigger:
                "body:has(:iframe body[is-ready=true]) .o_menu_systray button:contains('Edit')",
            run: "click",
        },
        {
            content: "Click Edit to start designing your homepage.",
            trigger: ".o_edit_website_dropdown_item",
            run: "click",
        },
        {
            content: "Check that we are in edit mode",
            trigger: ".o_builder_sidebar_open",
        },
    ];
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
        },
        {
            trigger: `:iframe ${trigger}`,
            content: "Click on a snippet to access its options menu.",
            tooltipPosition: position,
            run: "click",
        },
    ];
}
export function clickOnSave(timeout = 50000, withContains = true) {
    return [
        {
            trigger: ".o-snippets-menu:not(:has(.o_we_ongoing_insertion))",
        },
        {
            trigger: "body:not(:has(.o_dialog))",
        },
        {
            trigger: withContains
                ? "button[data-action=save]:enabled:contains(save)"
                : "button[data-action=save]:enabled",
            content: "Good job! It's time to save your work.",
            run: "click",
            timeout,
        },
        {
            trigger: "body:not(.o_builder_open)",
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
export function clickOnText(snippet, element) {
    return [
        {
            trigger: ":iframe body .odoo-editor-editable",
        },
        {
            trigger: snippet.id ? `:iframe #wrapwrap .${snippet.id} ${element}` : snippet,
            content: "Click on a text to start editing it.",
            run: "click",
        },
        {
            trigger: "#customize-tab.active",
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
    const insertSnippetSteps = [
        {
            trigger: ".o_builder_sidebar_open",
        },
    ];
    const snippetIDSelector = snippet.id
        ? `[data-snippet-id="${snippet.id}"]`
        : `[data-snippet-id^="${snippet.customID}_"]`;
    if (snippet.groupName) {
        insertSnippetSteps.push(
            {
                content: `Click on the ${blockEl} category.`,
                trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_groups .o_snippet[name="${blockEl}"].o_draggable .o_snippet_thumbnail_area`,
                tooltipPosition: position,
                run: "click",
            },
            {
                content: `Click on the ${snippet.name} building block.`,
                // FIXME `:not(.d-none)` should obviously not be needed but it seems
                // currently needed when using a tour in user/interactive mode.
                trigger: `.modal .show:iframe .o_snippet_preview_wrap${snippetIDSelector}:not(.d-none)`,
                tooltipPosition: "top",
                run: "click",
            }
        );
    } else {
        insertSnippetSteps.push({
            content: `Drag the ${blockEl} block and drop it at the bottom of the page.`,
            trigger: `.o_block_tab:not(.o_we_ongoing_insertion) #snippet_content .o_snippet[name="${blockEl}"].o_draggable .o_snippet_thumbnail`,
            tooltipPosition: position,
            run: "drag_and_drop :iframe #wrapwrap > footer",
        });
    }

    if (!ignoreLoading) {
        insertSnippetSteps.push({
            trigger: ".o_website_preview :iframe:not(:has(.o_loading_screen))",
        });
    }

    return insertSnippetSteps;
}

export function goBackToBlocks() {
    return {
        trigger: "button[data-name='blocks']",
        content: "Click here to go back to block tab.",
        run: "click",
    };
}

export function goToTheme() {
    return [
        {
            trigger: ".o-website-builder_sidebar",
        },
        {
            trigger: "button[data-name='theme']",
            content: "Go to the Theme tab",
            run: "click",
        },
        {
            content: "Check that the theme tab is active",
            trigger: ".o-tab-content .options-container [data-action-id='switchTheme']",
        },
    ];
}

export function selectHeader() {
    return {
        trigger: `:iframe header#top`,
        content: "Click on this header to configure it.",
        run: "click",
    };
}

export function unfoldOptionsGroup(name) {
    return [
        {
            content: `Unfold the "${name}" group`,
            trigger: `.options-container[data-container-title="${name}"] .options-container-label i.fa-caret-right`,
            run: "click",
        },
    ];
}

export function getClientActionUrl(path, edition) {
    let url = `/odoo/action-website.website_preview`;
    if (path) {
        url += `?path=${encodeURIComponent(path)}`;
    }
    if (edition) {
        url += `${path ? "&" : "?"}enable_editor=1`;
    }
    return url;
}

export function clickOnExtraMenuItem(stepOptions, backend = false) {
    return Object.assign(
        {
            content: "Click on the extra menu dropdown toggle if it is there",
            trigger: `${backend ? ":iframe" : ""} .top_menu`,
            async run(actions) {
                // Note: the button might not exist (it only appear if there is
                // many menu items).
                const extraMenuButton = this.anchor.querySelector(".o_extra_menu_items a.nav-link");
                // Don't click on the extra menu button if it's already visible.
                if (extraMenuButton && !extraMenuButton.classList.contains("show")) {
                    const dropdownFullyOpen = Promise.withResolvers();
                    extraMenuButton.addEventListener(
                        "shown.bs.dropdown",
                        dropdownFullyOpen.resolve,
                        { once: true }
                    );
                    await actions.click(extraMenuButton);
                    await dropdownFullyOpen.promise;
                }
            },
        },
        stepOptions
    );
}

export const waitForEditMode = {
    content: "Wait for the edit mode to be started",
    trigger: ".o_builder_sidebar_open",
    timeout: 30000,
};

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
        steps: () => {
            const tourSteps = [...steps()];
            // Note: for both non edit mode and edit mode, we set a high timeout for the
            // first step. Indeed loading both the backend and the frontend (in the
            // iframe) and potentially starting the edit mode can take a long time in
            // automatic tests. We'll try and decrease the need for this high timeout
            // of course.
            if (options.edition) {
                tourSteps.unshift(waitForEditMode);
            } else {
                tourSteps[0].timeout = 20000;
            }
            return tourSteps;
        },
    });
}

export function registerThemeHomepageTour(name, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    return registerWebsitePreviewTour(
        "homepage", // it overrides the community tour with the associated theme tour
        {},
        () => [
            ...clickOnEditAndWaitEditMode(),
            // FIXME(?) this should probably reuse the prepend_trigger function
            // so that we do check that we are really on the homepage.
            ...steps(),
            ...goToTheme(),
            ...clickOnSave(),
        ]
    );
}

export function registerBackendAndFrontendTour(name, options, steps) {
    if (typeof steps !== "function") {
        throw new Error(`tour.steps has to be a function that returns TourStep[]`);
    }
    if (window.location.pathname === "/odoo") {
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
        ...options,
        steps: () => steps(),
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
    return [
        {
            content: `Click on the website switch to switch to website '${websiteName}'`,
            trigger: ".o_website_switcher_container button",
            run: "click",
        },
        {
            trigger: `:iframe html:not([data-website-id="${websiteId}"])`,
        },
        {
            content: `Switch to website '${websiteName}'`,
            trigger: `.o-dropdown--menu .dropdown-item[data-website-id="${websiteId}"]:contains("${websiteName}")`,
            run: "click",
        },
        {
            content: "Wait for the iframe to be loaded",
            // The page reload generates assets for the new website, it may take
            // some time
            timeout: 20000,
            trigger: `:iframe html[data-website-id="${websiteId}"]`,
        },
    ];
}

export function switchToLang(lang) {
    return [
        {
            content: `Switch to ${lang}`,
            trigger: `:iframe .js_change_lang[data-url_code^='${lang}']`,
            // After clicking a language link, the iframe navigates to a new document.
            // We must wait for the old contentDocument to be replaced and the new
            // one to be fully loaded before proceeding, otherwise the next steps
            // may run against the old (unloading) or partially loaded document.
            async run({ anchor, click }) {
                const iframe = anchor.ownerDocument.defaultView.frameElement;
                const oldDoc = iframe.contentDocument;
                await click(anchor);
                while (!iframe.contentDocument || iframe.contentDocument === oldDoc) {
                    await new Promise((r) => setTimeout(r, 50));
                }
                while (iframe.contentDocument.readyState !== "complete") {
                    await new Promise((r) => setTimeout(r, 50));
                }
            },
        },
        {
            content: `Wait until ${lang} is applied`,
            trigger: `:iframe html[lang^="${lang}"]`,
        },
    ];
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
    const websiteIdMapping = JSON.parse(cookie.get("websiteIdMapping") || "{}");
    const websiteId = websiteIdMapping[websiteName];
    return switchWebsite(websiteId, websiteName);
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
export function openLinkPopup({
    trigger,
    runClick = true,
    url = "/",
    label = "",
    focusNodeIndex = 1,
    edit = false,
    remove = false,
} = {}) {
    const linkPopoverTrigger = (label, url) =>
        `.o-we-linkpopover .o_we_link_preview:has(.o_we_url_link${
            label ? `:contains(${label})` : ""
        }[href='${url}'])`;
    const steps = [
        {
            content: `Open '${label}' link popup`,
            trigger,
            async run({ click }) {
                if (runClick) {
                    await click();
                }
                const el = this.anchor;
                const sel = el.ownerDocument.getSelection();
                sel.collapse(el.childNodes[focusNodeIndex], 1);
                el.focus();
            },
        },
        {
            content: "Popover should be shown",
            trigger: linkPopoverTrigger(label, url),
        },
    ];
    if (edit || remove) {
        steps.push({
            content: "Click on Edit Link in Popover",
            trigger: `${linkPopoverTrigger(label, url)} .o_we_edit_link`,
            run: "click",
        });
    }
    if (edit && edit.length > 0) {
        steps.push(
            {
                content: `Type the link URL ${edit}`,
                trigger: ".o-we-linkpopover .o_we_href_input_link, .modal #url_input",
                run: `edit ${edit}`,
            },
            {
                content: "Save the link by clicking on Apply button",
                trigger: ".o-we-linkpopover .o_we_apply_link, .modal-footer button:text(Continue)",
                run: "click",
            },
            {
                trigger: linkPopoverTrigger(null, edit),
            }
        );
    }
    if (remove) {
        steps.push(
            {
                content: "Click on Remove Link in Popover",
                trigger: `.o-we-linkpopover .o_link_popover_container:has(.input-group) .o_we_remove_link`,
                run: "click",
            },
            {
                content: "Ensure popover is closed",
                trigger: ".o-overlay-container:not(:visible:has(.o-we-linkpopover))",
            }
        );
    }
    return steps;
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
            const range = document.createRange();
            const selection = this.anchor.ownerDocument.getSelection();
            range.selectNodeContents(this.anchor);
            selection.removeAllRanges();
            selection.addRange(range);
            this.anchor.closest(".odoo-editor-editable").dispatchEvent(
                new MouseEvent("pointerup", {
                    bubbles: true,
                    cancelable: true,
                })
            );
            await actions.click();
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
            trigger: `.o-we-toolbar button[title="${button}"], .o-we-toolbar button[name="${button}"]`,
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

export function changeBackgroundShape(shape = "html_builder/Connections/01") {
    return [
        {
            content: "Open Background Shape selector",
            trigger: "div[data-label='Background'] ~ div[data-label='Shape'] button.o-hb-btn",
            run: "click",
        },
        {
            content: "Wait for panel to open",
            trigger: ".hb-sliding-panel.d-block",
        },
        {
            content: "Pick a Background Shape",
            trigger: `.o_pager_container .o-hb-bg-shape-btn [data-action-id='setBackgroundShape'][data-action-value='${shape}']`,
            run: "click",
        },
        {
            content: "Wait for panel to close",
            trigger: "body:not(:has(.hb-panel-slide-out))",
        },
    ];
}

export function changeImageShape(shape = "html_builder/geometric/geo_shuriken") {
    return [
        {
            content: "Open Image Shape selector",
            trigger: "div[data-label='Media'] ~ div[data-label='Shape'] button.o-hb-btn",
            run: "click",
        },
        {
            content: "Wait for panel to open",
            trigger: ".hb-sliding-panel.d-block",
        },
        {
            content: "Pick an Image Shape",
            trigger: `.o_pager_container .o-hb-img-shape-btn [data-action-id='setImageShape'][data-action-value='${shape}']`,
            run: "click",
        },
        {
            content: "Wait for panel to close",
            trigger: ".options-container:visible",
        },
    ];
}

/**
 *
 * @param {string} trigger - selector
 * @returns step
 */
export function openPowerbox(trigger) {
    return {
        content: "Show the powerbox",
        trigger,
        async run(actions) {
            await actions.editor("/");
            const wrapwrap = this.anchor.closest("#wrapwrap");
            wrapwrap.dispatchEvent(
                new InputEvent("input", {
                    inputType: "insertText",
                    data: "/",
                })
            );
        },
    };
}
