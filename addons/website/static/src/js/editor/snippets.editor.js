/** @odoo-modules **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef, useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import weSnippetEditor from "@web_editor/js/editor/snippets.editor";
import wSnippetOptions from "@website/js/editor/snippets.options";
import * as OdooEditorLib from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { Component, onMounted, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { applyTextHighlight, switchTextHighlight } from "@website/js/text_processing";
import { registry } from "@web/core/registry";

const snippetsEditorRegistry = registry.category("snippets_editor");
snippetsEditorRegistry.add("no_parent_editor_snippets", ["s_popup", "o_mega_menu"]);

const getDeepRange = OdooEditorLib.getDeepRange;
const getTraversedNodes = OdooEditorLib.getTraversedNodes;

const FontFamilyPickerUserValueWidget = wSnippetOptions.FontFamilyPickerUserValueWidget;

const ANIMATED_TEXT_SELECTOR = ".o_animated_text";
const HIGHLIGHTED_TEXT_SELECTOR = ".o_text_highlight";

export class WebsiteSnippetsMenu extends weSnippetEditor.SnippetsMenu {

    static custom_events = Object.assign({}, weSnippetEditor.SnippetsMenu.custom_events, {
        'service_context_get': '_onServiceContextGet',
        'get_switchable_related_views': '_onGetSwitchableRelatedViews',
        'gmap_api_request': '_onGMapAPIRequest',
        'gmap_api_key_request': '_onGMapAPIKeyRequest',
        'reload_bundles': '_onReloadBundles',
    });

    static tabs = Object.assign({}, weSnippetEditor.SnippetsMenu.tabs, {
        THEME: 'theme',
    });
    static optionsTabStructure = [
        ['theme-colors', _t("Colors")],
        ['website-settings', _t("Website")],
        ['theme-paragraph', _t("Paragraph")],
        ['theme-headings', _t("Headings")],
        ['theme-button', _t("Button")],
        ['theme-link', _t("Link")],
        ['theme-input', _t("Input Fields")],
        ['theme-advanced', _t("Advanced")],
    ];

    static props = {
        ...weSnippetEditor.SnippetsMenu.props,
        getSwitchableRelatedViews: { type: Function },
    };

    static template = "website.SnippetsMenu";

    /**
     * @override
     */
    setup() {
        super.setup();
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this.websiteService = useService("website");
        this._notActivableElementsSelector += ', .o_mega_menu_toggle';

        onWillStart(async () => {
            this.isDesigner = await user.hasGroup("website.group_website_designer");
        });

        // Displays the button that allows to highlight the animated text if
        // there is animated text in the page.
        useEffect(
            () => {
                this.state.hasAnimatedText = !!this.getEditableArea().find('.o_animated_text').length;
            },
            () => [this.state.isTextAnimated],
        );
    }
    /**
     * @override
     */
    async start() {
        if (this.$body[0].ownerDocument !== this.ownerDocument) {
            this.$body.on('click.snippets_menu', '*', this._onClick);
        }
        await super.start(...arguments);

        this.__onSelectionChange = ev => {
            this.state.isTextAnimated = this._getTextOptionState(ANIMATED_TEXT_SELECTOR);
            this.state.isTextHighlighted = this._getTextOptionState(HIGHLIGHTED_TEXT_SELECTOR);
        };
        this.$body[0].ownerDocument.addEventListener('selectionchange', this.__onSelectionChange);

        // Even if we prevented the drag via the css, we have to override the
        // dragstart event because if one of the image ancestor has a dragstart
        // listener, the dragstart handler can be called with the image as
        // target. So we didn't prevent the drag with the css but with the
        // following handler.
        this.__onDragStart = ev => {
            if (ev.target.nodeName === "IMG") {
                ev.preventDefault();
                ev.stopPropagation();
            }
        };
        this.$body[0].addEventListener("dragstart", this.__onDragStart);

        this._adaptHighlightOnEdit = throttleForAnimation(switchTextHighlight);

        // Used to adjust highlight SVGs when the text is edited.
        this.textHighlightObserver = new MutationObserver(mutations => {
            // We only update SVGs when the mutation targets text content
            // (including all mutations leads to infinite loop since the
            // highlight adjustment will also trigger observed mutations).
            let isSVGMutation = false;
            let isNewContentMutation = false;
            const textHighlightEls = new Set();
            for (const mutation of mutations) {
                for (const addedNode of mutation.addedNodes) {
                    const addedHighlightNode = addedNode.classlist?.contains("o_text_highlight")
                        ? addedNode
                        : addedNode.querySelector?.(":scope .o_text_highlight");
                    if (addedHighlightNode) {
                        // E.g. When applying the split on a node with text
                        // highlights, the `oEnter` command will split the node
                        // and its parents correctly, which leads to duplicated
                        // highlight items that the observer should also handle.
                        // The goal here is to adapt these elements too.
                        textHighlightEls.add(addedHighlightNode);
                        isNewContentMutation = true;
                    }
                    if (addedNode.nodeName === "svg") {
                        isSVGMutation = true;
                    }
                }
                // Get the "text highlight" top element affected by mutations.
                const mutationTarget = mutation.target.parentElement?.closest(".o_text_highlight")
                    || mutation.target.nodeType === Node.ELEMENT_NODE
                    && mutation.target.querySelector(":scope .o_text_highlight");
                if (mutationTarget) {
                    textHighlightEls.add(mutationTarget);
                }
            }
            if (!isSVGMutation || isNewContentMutation) {
                for (const targetEl of textHighlightEls) {
                    this._adaptHighlightOnEdit(targetEl);
                }
            }
        });

        this.textHighlightObserver.observe(this.options.editable[0], {
            attributes: false,
            childList: true,
            characterData: true,
            subtree: true,
        });
    }
    /**
     * @override
     */
    get invalidateSnippetCache() {
        return this.websiteService.invalidateSnippetCache;
    }
    set invalidateSnippetCache(value) {
        this.websiteService.invalidateSnippetCache = value;
    }
    /**
     * @override
     */
    onWillUnmount() {
        super.onWillUnmount(...arguments);
        this.$body[0].ownerDocument.removeEventListener('selectionchange', this.__onSelectionChange);
        this.$body[0].removeEventListener("dragstart", this.__onDragStart);
        this.$body[0].classList.remove('o_animated_text_highlighted');
        clearTimeout(this._hideBackendNavbarTimeout);
    }

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    async cleanForSave() {
        this.textHighlightObserver.disconnect();
        const getFromEditable = selector => this.options.editable[0].querySelectorAll(selector);
        // Clean unstyled translations
        return super.cleanForSave(...arguments).then(() => {
            for (const el of getFromEditable('.o_translation_without_style')) {
                el.classList.remove('o_translation_without_style');
                if (el.dataset.oeTranslationSaveSha) {
                    el.dataset.oeTranslationSourceSha = el.dataset.oeTranslationSaveSha;
                    delete el.dataset.oeTranslationSaveSha;
                }
            }
            // Adapt translation values for `select` > `options`s and remove all
            // temporary `.o_translation_select` elements.
            for (const optionsEl of getFromEditable('.o_translation_select')) {
                const selectEl = optionsEl.nextElementSibling;
                const translatedOptions = optionsEl.children;
                const selectOptions = selectEl.tagName === 'SELECT' ? [...selectEl.options] : [];
                if (selectOptions.length === translatedOptions.length) {
                    selectOptions.map((option, i) => {
                        option.text = translatedOptions[i].textContent;
                    });
                }
                optionsEl.remove();
            }
        });
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeSnippetTemplates(html) {
        const $html = $(html);

        // TODO Remove in master. This patches the snippet move selectors.
        const oldSelector = ".s_showcase .row:not(.s_col_no_resize) > div";
        let optionEl = $html[0].querySelector(`[data-js="SnippetMove"][data-selector*="${oldSelector}"]`);
        if (optionEl) {
            const newSelector = oldSelector.replace(".row", ".row .row");
            optionEl.dataset.selector = optionEl.dataset.selector.replace(oldSelector, newSelector);
        }
        const oldExclude = ".s_showcase .row > div";
        optionEl = $html[0].querySelector(`[data-js="SnippetMove"][data-exclude*="${oldExclude}"]`);
        if (optionEl) {
            const newExclude = oldExclude.replace(".row", ".row .row");
            optionEl.dataset.exclude = optionEl.dataset.exclude.replace(oldExclude, newExclude);
        }

        // TODO remove in master: changing the `data-apply-to` attribute of the
        // grid spacing option so it is not applied on inner rows.
        const gridSpacingOptionEls = html.querySelectorAll('[data-css-property="row-gap"], [data-css-property="column-gap"]');
        gridSpacingOptionEls.forEach(gridSpacingOptionEl => gridSpacingOptionEl.dataset.applyTo = ".row.o_grid_mode");

        const toFind = $html.find("we-fontfamilypicker[data-variable]").toArray();
        const fontVariables = toFind.map((el) => el.dataset.variable);
        FontFamilyPickerUserValueWidget.prototype.fontVariables = fontVariables;

        // TODO remove in master: adds back the "Layout" and "Content Width"
        // options on some carousels.
        const layoutOptionEl = html.querySelector('[data-js="layout_column"][data-selector="section"]');
        const containerWidthOptionEl = html.querySelector('[data-js="ContainerWidth"][data-selector="section"]');
        if (layoutOptionEl) {
            layoutOptionEl.dataset.selector += ", section.s_carousel_wrapper .carousel-item";
        }
        if (containerWidthOptionEl) {
            containerWidthOptionEl.dataset.selector += ", .s_carousel .carousel-item";
        }

        return super._computeSnippetTemplates(html);
    }
    /**
     * Depending of the demand, reconfigure they gmap key or configure it
     * if not already defined.
     *
     * @private
     * @param {boolean} [alwaysReconfigure=false]
     * @param {boolean} [configureIfNecessary=false]
     */
    async _configureGMapAPI({alwaysReconfigure, configureIfNecessary}) {
        if (!alwaysReconfigure && !configureIfNecessary) {
            // TODO should review, parameters are weird... only one necessary?
            return false;
        }

        const apiKey = await new Promise(resolve => {
            this.websiteService.websiteRootInstance.trigger_up("gmap_api_key_request", {
                onSuccess: key => resolve(key),
            });
        });
        const apiKeyValidation = apiKey ? await this._validateGMapAPIKey(apiKey) : {
            isValid: false,
            message: undefined,
        };
        if (!alwaysReconfigure && configureIfNecessary && apiKey && apiKeyValidation.isValid) {
            return false;
        }

        const websiteId = this.websiteService.currentWebsite.id;

        function applyError(message) {
            const $apiKeyInput = this.find('#api_key_input');
            const $apiKeyHelp = this.find('#api_key_help');
            $apiKeyInput.addClass('is-invalid');
            $apiKeyHelp.empty().text(message);
        }

        const GoogleMapAPIKeyDialog = class extends Component {
            static template = "website.s_google_map_modal";
            static components = { Dialog };
            static props = {
                onMounted: Function,
                close: Function,
                confirm: Function
            };
            setup() {
                this.modalRef = useChildRef();
                this.state = useState({ apiKey: apiKey });
                this.apiKeyInput = useRef("apiKeyInput");
                onMounted(() => this.props.onMounted(this.modalRef));
            }
            onClickSave() {
                this.props.confirm(this.modalRef, this.state.apiKey);
                this.props.close();
            }
        };

        return new Promise(resolve => {
            let invalidated = false;
            this.dialog.add(GoogleMapAPIKeyDialog, {
                onMounted: (modalRef) => {
                    if (!apiKeyValidation.isValid && apiKeyValidation.message) {
                        applyError.call($(modalRef.el), apiKeyValidation.message);
                    }
                },
                confirm: async (modalRef, valueAPIKey) => {
                    if (!valueAPIKey) {
                        applyError.call($(modalRef.el), _t("Enter an API Key"));
                        return;
                    }
                    const $button = $(modalRef.el).find("button");
                    $button.prop('disabled', true);
                    const res = await this._validateGMapAPIKey(valueAPIKey);
                    if (res.isValid) {
                        await this.orm.write("website", [websiteId], {google_maps_api_key: valueAPIKey});
                        invalidated = true;
                        return true;
                    } else {
                        applyError.call($(modalRef.el), res.message);
                    }
                    $button.prop("disabled", false);
                }
            }, {
                onClose: () => resolve(invalidated),
            });
        });
    }
    /**
     * @private
     */
    async _validateGMapAPIKey(key) {
        try {
            const response = await fetch(`https://maps.googleapis.com/maps/api/staticmap?center=belgium&size=10x10&key=${encodeURIComponent(key)}`);
            const isValid = (response.status === 200);
            return {
                isValid: isValid,
                message: !isValid &&
                    _t("Invalid API Key. The following error was returned by Google: %(error)s", {error: await response.text()}),
            };
        } catch {
            return {
                isValid: false,
                message: _t("Check your connection and try again"),
            };
        }
    }
    /**
     * @override
     */
    _getDragAndDropOptions(options = {}) {
        // TODO: This is currently not in use by Odoo's D&D
        // There is currently no way in Odoo D&D to offset the edge scrolling.
        // When there is, this code should be adapted.
        const finalOptions = super._getDragAndDropOptions(...arguments);
        if (!options.offsetElements || !options.offsetElements.$top) {
            const $header = $('#top');
            if ($header.length) {
                finalOptions.offsetElements = finalOptions.offsetElements || {};
                finalOptions.offsetElements.$top = $header;
            }
        }
        return finalOptions;
    }
    /**
     * @private
     * @param {OdooEvent} ev
     * @param {string} gmapRequestEventName
     */
    async _handleGMapRequest(ev, gmapRequestEventName) {
        ev.stopPropagation();
        const reconfigured = await this._configureGMapAPI({
            alwaysReconfigure: ev.data.reconfigure,
            configureIfNecessary: ev.data.configureIfNecessary,
        });
        this.websiteService.websiteRootInstance.trigger_up(gmapRequestEventName, {
            refetch: reconfigured,
            editableMode: true,
            onSuccess: key => ev.data.onSuccess(key),
        });
    }
    /**
     * Returns the text option element wrapping the selection if it exists.
     *
     * @private
     * @param {String} selector
     * @return {Element|false}
     */
    _getSelectedTextElement(selector) {
        const editable = this.options.wysiwyg.$editable[0];
        const textOptionNode = getTraversedNodes(editable).find(n => n.parentElement.closest(selector));
        return textOptionNode ? textOptionNode.parentElement.closest(selector) : false;
    }
    /**
     * @private
     * @return {Selection|null}
     */
    _getSelection() {
        return this.options.wysiwyg.odooEditor.document.getSelection();
    }
    /**
     * @override
     */
    _addToolbar() {
        super._addToolbar(...arguments);
        this.state.animatedTextHighlighted = this.$body[0].classList.contains("o_animated_text_highlighted");
        this.state.isTextAnimated = this._getTextOptionState(ANIMATED_TEXT_SELECTOR);
        this.state.isTextHighlighted = this._getTextOptionState(HIGHLIGHTED_TEXT_SELECTOR);

        // As the toolbar displays css variable that are customizable by users,
        // we have the recompute the font size selector values.
        this.options.wysiwyg.odooEditor.computeFontSizeSelectorValues();
    }
    /**
    * @override
    */
    _checkEditorToolbarVisibility(e) {
        super._checkEditorToolbarVisibility(...arguments);
        // Close the option's dropdowns manually on outside click if any open.
        this._toolbarWrapperEl.querySelectorAll(".dropdown-toggle.show").forEach(toggleEl => {
            Dropdown.getOrCreateInstance(toggleEl).hide();
        });
    }
    /**
     * Returns true if the selected text matches the selector.
     *
     * @private
     */
    _getTextOptionState(textSelector) {
        if (!this._isValidSelection(this._getSelection())) {
            return;
        }
        return !!this._getSelectedTextElement(textSelector);
    }
    /**
     * @private
     * @param {Node} node
     * @return {Boolean}
     */
    _isValidSelection(sel) {
        return sel.rangeCount && [...this.getEditableArea()].some(el => el.contains(sel.anchorNode));
    }
    /**
     * @override
     */
    _isMobile() {
        return this.websiteService.context.isMobile;
    }
    /**
     * This callback type is used to identify the function used to apply some
     * actions on the activated text snippet.
     *
     * @callback TextOptionCallback
     * @param {jQuery} $snippet The selected text element on which the option
     * should be applied.
     */
    /**
     * Used to handle "text options" button click according to whether the
     * selected text has the option activated or not.
     *
     * @private
     * @param {string} classSelector
     * @param {Array<String>} optionClassList
     * @param {TextOptionCallback} textOptionsPostActivate callback to trigger
     * actions when the text snippet is activated.
     * @returns {boolean} true if the option was applied, false if it was
     * removed or could not be applied.
     */
    _handleTextOptions(classSelector, optionClassList, textOptionsPostActivate = () => {}) {
        const sel = this._getSelection();
        if (!this._isValidSelection(sel)) {
            return false;
        }
        const editable = this.options.wysiwyg.$editable[0];
        const range = getDeepRange(editable, {splitText: true, select: true, correctTripleClick: true});
        // Check if the text has already the current option activated.
        let selectedTextEl = this._getSelectedTextElement(classSelector);
        if (selectedTextEl) {
            const restoreCursor = OdooEditorLib.preserveCursor(this.$body[0].ownerDocument);
            // Unwrap the selected text content and disable the option.
            const selectedTextParent = selectedTextEl.parentNode;
            while (selectedTextEl.firstChild) {
                const child = selectedTextEl.firstChild;
                // When the text highlight option is activated, the text wrapper
                // may contain SVG elements. They should be removed too...
                if (child.nodeType === Node.ELEMENT_NODE && child.className.includes("o_text_highlight_item")) {
                    child.after(...[...child.childNodes].filter((node) => node.tagName !== "svg"));
                    child.remove();
                }
                selectedTextParent.insertBefore(selectedTextEl.firstChild, selectedTextEl);
            }
            selectedTextParent.removeChild(selectedTextEl);
            // Update the option's UI.
            this.options.wysiwyg.odooEditor.historyResetLatestComputedSelection();
            this.options.wysiwyg.odooEditor.historyStep(true);
            restoreCursor();
            if (this.options.enableTranslation) {
                $(selectedTextParent).trigger("content_changed");
            }
            return false;
        } else {
            if (sel.getRangeAt(0).collapsed) {
                return;
            }
            selectedTextEl = document.createElement("span");
            selectedTextEl.classList.add(...optionClassList);
            let $snippet = null;
            try {
                range.surroundContents(selectedTextEl);
                $snippet = $(selectedTextEl);
            } catch {
                // This try catch is needed because 'surroundContents' may
                // fail when the range has partially selected a non-Text node.
                if (range.commonAncestorContainer.textContent === range.toString()) {
                    const $commonAncestor = $(range.commonAncestorContainer);
                    $commonAncestor.wrapInner(selectedTextEl);
                    $snippet = $commonAncestor.find(classSelector);
                }
            }
            if ($snippet) {
                $snippet[0].normalize();
                this._activateSnippet($snippet, false).then(() => {
                    textOptionsPostActivate($snippet);
                });
                this.options.wysiwyg.odooEditor.historyStep();
                return true;
            } else {
                this.notification.add(
                    _t("Cannot apply this option on current text selection. Try clearing the format and try again."),
                    { type: 'danger', sticky: true }
                );
            }
            return false;
        }
    }
    /**
     * @private
     * @param {string} textSelector;
     */
    _getOptionTextClass(textSelector) {
        return textSelector.slice(1);
    }
    /**
     * The goal here is to disable parents editors for snippets that should not
     * display their parents options.
     *
     * @override
     */
     _allowParentsEditors($snippet) {
        return super._allowParentsEditors(...arguments) && !snippetsEditorRegistry.get("no_parent_editor_snippets")
            .some(snippetClass => $snippet[0].classList.contains(snippetClass));
    }
    /**
     * @override
     */
    _insertDropzone($hook) {
        var $hookParent = $hook.parent();
        var $dropzone = super._insertDropzone(...arguments);
        $dropzone.attr('data-editor-message-default', $hookParent.attr('data-editor-message-default'));
        $dropzone.attr('data-editor-message', $hookParent.attr('data-editor-message'));
        $dropzone.attr('data-editor-sub-message', $hookParent.attr('data-editor-sub-message'));
        return $dropzone;
    }
    /**
     * @override
     */
    _updateDroppedSnippet($target) {
        // Build the highlighted text content for the snippets.
        for (const textEl of $target[0]?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
        return super._updateDroppedSnippet(...arguments);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onGMapAPIRequest(ev) {
        this._handleGMapRequest(ev, 'gmap_api_request');
    }
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onGMapAPIKeyRequest(ev) {
        this._handleGMapRequest(ev, 'gmap_api_key_request');
    }
    /**
     * @private
     */
    _onThemeTabClick(ev) {
        this._enableFakeOptionsTab(WebsiteSnippetsMenu.tabs.THEME);
    }
    /**
     * @override
     */
    _onOptionsTabClick(ev) {
        if (!ev.currentTarget.classList.contains('active')) {
            this._activateSnippet(false);
            this._mutex.exec(async () => {
                const switchableViews = await this.props.getSwitchableRelatedViews();
                if (switchableViews.length) {
                    // These do not need to be awaited as we're in teh context
                    // of the mutex.
                    this._activateSnippet(this.$body.find('#wrapwrap > main'));
                    return;
                }
                let $pageOptionsTarget = $();
                let i = 0;
                const pageOptions = this.templateOptions.filter(template => template.data.pageOptions);
                while (!$pageOptionsTarget.length && i < pageOptions.length) {
                    $pageOptionsTarget = pageOptions[i].selector.all();
                    i++;
                }
                if ($pageOptionsTarget.length) {
                    this._activateSnippet($pageOptionsTarget);
                } else {
                    this._activateEmptyOptionsTab();
                }
            });
        }
    }
    /**
     * @private
     * @param {Event} ev
     */
    _onAnimateTextClick(ev) {
        const active = this._handleTextOptions(ANIMATED_TEXT_SELECTOR, [
            this._getOptionTextClass(ANIMATED_TEXT_SELECTOR),
            "o_animate",
            "o_animate_preview",
            "o_anim_fade_in",
        ]);
        this.state.isTextAnimated = active;
    }
    /**
     * @private
     */
    _onHighlightAnimatedTextClick(ev) {
        const highlighted = this.$body[0].classList.toggle('o_animated_text_highlighted');
        this.state.animatedTextHighlighted = highlighted;
        $(ev.target).toggleClass('fa-eye fa-eye-slash').toggleClass('text-success');
    }
    /**
     * @private
     */
    _onTextHighlightClick() {
        // To be able to open the highlights grid immediately, we need to
        // prevent the `_onClick()` handler from closing the widget (using
        // the `_closeWidgets()` method) right after opening it.
        this._closeWidgets();
        const active = this._handleTextOptions(
            HIGHLIGHTED_TEXT_SELECTOR,
            [
                this._getOptionTextClass(HIGHLIGHTED_TEXT_SELECTOR),
                "o_text_highlight_underline",
                "o_translate_inline",
            ],
            ($snippet) => {
                // TODO should be reviewed
                $snippet.data("snippet-editor")?.trigger_up("option_update", {
                    optionName: "TextHighlight",
                    name: "new_text_highlight",
                });
            }
        );
        this.state.isTextHighlighted = active;
    }
    /**
     * On reload bundles, when it's from the theme tab, destroy any
     * snippetEditor as they might hold outdated style values. (e.g. color palettes).
     * We do not destroy the Theme tab editors as they should have the correct
     * values with their compute widget states.
     * NOTE: This is a bit janky, _computeWidgetState should modify the
     * option's widget to reflect the style accordingly. But since
     * color_palette widget is independent of the UserValueWidget, it's hard to
     * modify its style using the options events.
     *
     * @private
     */
    _onReloadBundles(ev) {
        const excludeSelector = this.constructor.optionsTabStructure.map(element => element[0]).join(', ');
        const oldSuccess = ev.data.onSuccess;
        ev.data.onSuccess = (...args) => {
            // Update the panel so that color previews reflect the ones used by the
            // edited content.
            this.props.setCSSVariables(this.el);
            oldSuccess(...args);
        };
        for (const editor of this.snippetEditors) {
            if (!editor.$target[0].matches(excludeSelector)) {
                if (this._currentTab === this.tabs.THEME) {
                    this._mutex.exec(() => {
                        editor.destroy();
                    });
                } else {
                    this._mutex.exec(async () => {
                        await editor.updateOptionsUI(true);
                    });
                }
            }
        }
    }
    /**
     * Notifies the website service that mobile preview is toggled.
     * This will toggle the iframe between mobile and desktop view.
     *
     * @private
     */
    _toggleMobilePreview() {
        this.websiteService.context.isMobile = !this.websiteService.context.isMobile;
    }
    /**
     * Used by legacy widgets to fetch the state of the mobile preview.
     *
     * @private
     * @param {CustomEvent} ev
     */
    _onServiceContextGet(ev) {
        ev.data.callback({
            isMobile: this.websiteService.context.isMobile,
        });
    }
    /**
     * Returns the list of views that can be toggled on the current page.
     *
     * @param {CustomEvent} ev
     */
    _onGetSwitchableRelatedViews(ev) {
        this.props.getSwitchableRelatedViews().then(ev.data.onSuccess);
    }
}

weSnippetEditor.SnippetEditor.include({
    layoutElementsSelector: [
        weSnippetEditor.SnippetEditor.prototype.layoutElementsSelector,
        '.s_parallax_bg',
        '.o_bg_video_container',
    ].join(','),

    /**
     * @override
     */
    getName() {
        if (this.$target[0].closest('[data-oe-field=logo]')) {
            return _t("Logo");
        }
        return this._super(...arguments);
    },
    /**
     * Changes some behaviors before the drag and drop.
     *
     * @private
     * @override
     * @returns {Function} a function that restores what was changed when the
     *  drag and drop is over.
     */
    _prepareDrag() {
        const restore = this._super(...arguments);
        // Remove the footer scroll effect if it has one (because the footer
        // dropzone flickers otherwise when it is in grid mode).
        const wrapwrapEl = this.$body[0].ownerDocument.defaultView.document.body.querySelector('#wrapwrap');
        const hasFooterScrollEffect = wrapwrapEl && wrapwrapEl.classList.contains('o_footer_effect_enable');
        if (hasFooterScrollEffect) {
            wrapwrapEl.classList.remove('o_footer_effect_enable');
            return () => {
                wrapwrapEl.classList.add('o_footer_effect_enable');
                restore();
            };
        }
        return restore;
    },
});

export default {
    SnippetsMenu: WebsiteSnippetsMenu,
};
