/** @odoo-modules **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { useChildRef } from "@web/core/utils/hooks";
import weSnippetEditor from "@web_editor/js/editor/snippets.editor";
import wSnippetOptions from "@website/js/editor/snippets.options";
import wUtils from "@website/js/utils";
import * as OdooEditorLib from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { throttleForAnimation } from "@web/core/utils/timing";
import { applyTextHighlight, switchTextHighlight } from "@website/js/text_processing";

const getDeepRange = OdooEditorLib.getDeepRange;
const getTraversedNodes = OdooEditorLib.getTraversedNodes;

const FontFamilyPickerUserValueWidget = wSnippetOptions.FontFamilyPickerUserValueWidget;

const wSnippetMenu = weSnippetEditor.SnippetsMenu.extend({
    events: Object.assign({}, weSnippetEditor.SnippetsMenu.prototype.events, {
        'click .o_we_customize_theme_btn': '_onThemeTabClick',
        'click .o_we_animate_text': '_onAnimateTextClick',
        'click .o_we_highlight_animated_text': '_onHighlightAnimatedTextClick',
        "click .o_we_text_highlight": "_onTextHighlightClick",
    }),
    custom_events: Object.assign({}, weSnippetEditor.SnippetsMenu.prototype.custom_events, {
        'gmap_api_request': '_onGMapAPIRequest',
        'gmap_api_key_request': '_onGMapAPIKeyRequest',
        'reload_bundles': '_onReloadBundles',
    }),
    tabs: Object.assign({}, weSnippetEditor.SnippetsMenu.prototype.tabs, {
        THEME: 'theme',
    }),
    optionsTabStructure: [
        ['theme-colors', _t("Colors")],
        ['website-settings', _t("Website")],
        ['theme-paragraph', _t("Paragraph")],
        ['theme-headings', _t("Headings")],
        ['theme-button', _t("Button")],
        ['theme-link', _t("Link")],
        ['theme-input', _t("Input Fields")],
        ['theme-advanced', _t("Advanced")],
    ],

    /**
     * @override
     */
    init() {
        this._super(...arguments);
        this.notification = this.bindService("notification");
        this.dialog = this.bindService("dialog");
    },
    /**
     * @override
     */
    async start() {
        await this._super(...arguments);

        this.__onSelectionChange = ev => {
            this._toggleTextOptionsButton(".o_we_animate_text");
            this._toggleTextOptionsButton(".o_we_text_highlight");
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

        // editor_has_snippets is, amongst other things, in charge of hiding the
        // backend navbar with a CSS animation. But we also need to make it
        // display: none when the animation finishes for efficiency but also so
        // that the tour tooltips pointing at the navbar disappear. This could
        // rely on listening to the transitionend event but it seems more future
        // proof to just add a delay after which the navbar is hidden.
        this._hideBackendNavbarTimeout = setTimeout(() => {
            this.el.ownerDocument.body.classList.add('editor_has_snippets_hide_backend_navbar');
        }, 500);

        this._adaptHighlightOnEdit = throttleForAnimation(this._adaptHighlightOnEdit.bind(this));

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
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$body[0].ownerDocument.removeEventListener('selectionchange', this.__onSelectionChange);
        this.$body[0].removeEventListener("dragstart", this.__onDragStart);
        this.$body[0].classList.remove('o_animated_text_highlighted');
        clearTimeout(this._hideBackendNavbarTimeout);
        this.el.ownerDocument.body.classList.remove('editor_has_snippets_hide_backend_navbar');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeSnippetTemplates: function (html) {
        const $html = $(html);
        const toFind = $html.find("we-fontfamilypicker[data-variable]").toArray();
        const fontVariables = toFind.map((el) => el.dataset.variable);
        FontFamilyPickerUserValueWidget.prototype.fontVariables = fontVariables;
        return this._super(...arguments);
    },
    /**
     * @override
     */
    _patchForComputeSnippetTemplates($html) {
        this._super(...arguments);

        // TODO adapt in master: as a stable fix we corrected the behavior of
        // the logo button that led to an error when switching from Text to
        // Logo. Remove me in master.
        const logoViewName = 'website.option_header_brand_logo';
        const logoButtonEl = $html.find(`[data-customize-website-views="${logoViewName}"]`)[0];
        if (logoButtonEl) {
            logoButtonEl.dataset.customizeWebsiteViews = `|website.option_header_brand_name|${logoViewName}`;
            logoButtonEl.dataset.resetViewArch = "true";
        }
        const brandSelectorEl = $html.find('[data-name="option_header_brand_none"]')[0]
            ?.closest("[data-selector]");
        if (brandSelectorEl) {
            brandSelectorEl.dataset.selector = brandSelectorEl.dataset.selector
                .replace('.navbar-brand.logo', '.navbar-brand');
        }

        // TODO adapt in master: as a stable imp we added a preview for the
        // "Effect" option of the "On Hover" animation option.
        const hoverEffectSelectEl = $html.find('[data-set-img-shape-hover-effect]')[0];
        delete hoverEffectSelectEl.dataset.noPreview;

        // TODO remove in master: as a stable fix we exclude the form fields
        // from the grid cell's Padding (Y, X) option.
        const gridColumnsEl = $html.find('[data-js="GridColumns"]')[0];
        if (gridColumnsEl) {
            gridColumnsEl.dataset.selector = ".row:not(.s_col_no_resize) > div";
        }

        // Remove the input-border-width-sm and input-border-width-lg from the input-border-width
        ['input-border-width-sm', 'input-border-width-lg'].forEach(variable => {
            const element = $html.find(
                `[data-selector='theme-input'] we-input[data-customize-website-variable][data-variable='${variable}']`
            )[0];
            element.remove();
        });

        // TODO remove in master: should be simply replaced by a
        // `data-text-selector` attribute to mark text options.
        const AnimationOptionEl = $html.find('[data-js="WebsiteAnimate"]')[0];
        const HighlightOptionEl = $html.find('[data-js="TextHighlight"]')[0];
        if (AnimationOptionEl) {
            AnimationOptionEl.dataset.textSelector = ".o_animated_text";
        }
        if (HighlightOptionEl) {
            HighlightOptionEl.dataset.textSelector = HighlightOptionEl.dataset.selector;
        }

        // TODO remove in master: see snippets.xml
        $html.find('we-checkbox[data-dependencies="!footer_copyright_opt"]')[0]?.remove();
        $html.find('[data-name="header_language_selector_none_opt"]')[0]?.remove();
        $html.find('we-select[data-dependencies="!header_language_selector_none_opt"]')[0]?.removeAttribute("data-dependencies");

        // TODO remove in master: changing the `data-apply-to` attribute of the
        // grid spacing option so it is not applied on inner rows.
        const $gridSpacingOptions = $html.find('[data-css-property="row-gap"], [data-css-property="column-gap"]');
        $gridSpacingOptions.attr("data-apply-to", ".row.o_grid_mode");

        // TODO remove in master and adapt XML.
        const contentAdditionEl = $html.find("#so_content_addition")[0];
        if (contentAdditionEl) {
            // Necessary to be able to drop "inner blocks" next to an image link.
            contentAdditionEl.dataset.dropNear += ", div:not(.o_grid_item_image) > a";
            // TODO remove in master
            // The class is added again here even though it has already been
            // added by the "searchbar_input_snippet_options" template. We are
            // doing it again because it was mistakenly translated into Dutch.
            contentAdditionEl.dataset.selector += ", .s_searchbar_input";
            contentAdditionEl.dataset.dropNear += ", .s_searchbar_input";
        }
        // TODO remove in master
        const snippetSaveOptionEl = $html.find("[data-js='SnippetSave']")[0];
        if (snippetSaveOptionEl) {
            snippetSaveOptionEl.dataset.selector += ", .s_searchbar_input";
        }
        // TODO remove in 18.0
        const navTabsStyleEl = $html.find(`[data-js="NavTabsStyle"]`)[0];
        if (navTabsStyleEl) {
            const divEl = document.createElement("div");
            divEl.setAttribute("data-js", "TabsNavItems");
            divEl.setAttribute("data-selector", ".nav-item");
            navTabsStyleEl.append(divEl);
        }
    },
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
            this.getParent()._websiteRootEvent("gmap_api_key_request", {
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

        let websiteId;
        this.trigger_up('context_get', {
            callback: ctx => websiteId = ctx['website_id'],
        });

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
                this.props.confirm(this.modalRef, this.state.apiKey, this.props.close);
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
                confirm: async (modalRef, valueAPIKey, close = undefined) => {
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
                        if (close) {
                            close();
                        } else {
                            resolve(true);
                        }
                    } else {
                        applyError.call($(modalRef.el), res.message);
                    }
                    $button.prop("disabled", false);
                }
            }, {
                onClose: () => resolve(invalidated),
            });
        });
    },
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
                    _t("Invalid API Key. The following error was returned by Google:") + " " + (await response.text()),
            };
        } catch {
            return {
                isValid: false,
                message: _t("Check your connection and try again"),
            };
        }
    },
    /**
     * @override
     */
    _getDragAndDropOptions(options = {}) {
        // TODO: This is currently not in use by Odoo's D&D
        // There is currently no way in Odoo D&D to offset the edge scrolling.
        // When there is, this code should be adapted.
        const finalOptions = this._super(...arguments);
        if (!options.offsetElements || !options.offsetElements.$top) {
            const $header = $('#top');
            if ($header.length) {
                finalOptions.offsetElements = finalOptions.offsetElements || {};
                finalOptions.offsetElements.$top = $header;
            }
        }
        return finalOptions;
    },
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
        this.getParent()._websiteRootEvent(gmapRequestEventName, {
            refetch: reconfigured,
            editableMode: true,
            onSuccess: key => ev.data.onSuccess(key),
        });
    },
    /**
     * @override
     */
    _updateRightPanelContent: function ({content, tab}) {
        this._super(...arguments);
        this.$('.o_we_customize_theme_btn').toggleClass('active', tab === this.tabs.THEME);
    },
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
    },
    /**
     * @private
     * @return {Selection|null}
     */
    _getSelection() {
        return this.options.wysiwyg.odooEditor.document.getSelection();
    },
    /**
     * @override
     */
    _addToolbar() {
        this._super(...arguments);
        this.$('#o_we_editor_toolbar_container > we-title > span').after($(`
            <we-button class="fa fa-fw o_we_link o_we_highlight_animated_text d-none
                ${this.$body.hasClass('o_animated_text_highlighted') ? 'fa-eye text-success' : 'fa-eye-slash'}"
                title="${_t('Highlight Animated Text')}"
                aria-label="Highlight Animated Text">
            </we-button>
        `));
        this._toggleTextOptionsButton(".o_we_animate_text");
        this._toggleHighlightAnimatedTextButton();
        this._toggleTextOptionsButton(".o_we_text_highlight");

        // As the toolbar displays css variable that are customizable by users,
        // we have the recompute the font size selector values.
        this.options.wysiwyg.odooEditor.computeFontSizeSelectorValues();
    },
    /**
    * @override
    */
    _checkEditorToolbarVisibility: function (e) {
        this._super(...arguments);
        // Close the option's dropdowns manually on outside click if any open.
        if (this._$toolbarContainer && this._$toolbarContainer.length) {
            this._$toolbarContainer[0].querySelectorAll(".dropdown-toggle.show").forEach(toggleEl => {
                Dropdown.getOrCreateInstance(toggleEl).hide();
            });
        }
    },
    /**
     * Activates & deactivates the button used to add text options, depending
     * on the selected element.
     *
     * @private
     */
    _toggleTextOptionsButton(selector) {
        if (!this._isValidSelection(this._getSelection())) {
            return;
        }
        const textOptionsButton = this.el.querySelector(selector);
        if (textOptionsButton) {
            textOptionsButton.classList.toggle("active", !!this._getSelectedTextElement(textOptionsButton.dataset.textSelector));
        }
    },
    /**
     * Displays the button that allows to highlight the animated text if there
     * is animated text in the page.
     *
     * @private
     */
    _toggleHighlightAnimatedTextButton() {
        const $animatedText = this.getEditableArea().find('.o_animated_text');
        this.$('#o_we_editor_toolbar_container .o_we_highlight_animated_text').toggleClass('d-none', !$animatedText.length);
    },
    /**
     * @private
     * @param {Node} node
     * @return {Boolean}
     */
    _isValidSelection(sel) {
        return sel.rangeCount && [...this.getEditableArea()].some(el => el.contains(sel.anchorNode));
    },
    /**
     * @override
     */
    _isMobile() {
        return wUtils.isMobile(this);
    },
    /**
     * This callback type is used to identify the function used to apply the
     * text option on a selected text.
     *
     * @deprecated
     * @callback TextOptionCallback
     * @param {HTMLElement} selectedTextEl The selected text element on which
     * the option should be applied.
     */
    /**
     * Used to handle "text options" button click according to whether the
     * selected text has the option activated or not.
     *
     * @private
     * @param {HTMLElement} targetEl
     * @param {Array<String>} optionClassList
     * @param {TextOptionCallback} applyTextOption callback function to set
     * text option's classes, updates...
     */
    _handleTextOptions(targetEl, optionClassList, applyTextOption = () => {}) {
        // TODO adapt in master
        const __handleTextOptionsPostActivate = this.__handleTextOptionsPostActivate;

        const classSelector = targetEl.dataset.textSelector;
        const sel = this._getSelection();
        if (!this._isValidSelection(sel)) {
            return;
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
            this._disableTextOptions(targetEl);
            this.options.wysiwyg.odooEditor.historyStep(true);
            restoreCursor();
            if (this.options.enableTranslation) {
                $(selectedTextParent).trigger("content_changed");
            }
        } else {
            if (sel.getRangeAt(0).collapsed) {
                return;
            }
            selectedTextEl = document.createElement("span");
            selectedTextEl.classList.add(...optionClassList);
            let $snippet = null;
            try {
                const commonAncestor = range.commonAncestorContainer;
                const ancestorElement =
                    commonAncestor.nodeType === 1 ? commonAncestor : commonAncestor.parentElement;
                const backgroundColorParentEl = ancestorElement.closest(
                    'font[style*="background-color"], font[style*="background-image"], font[class^="bg-"]'
                );
                if (backgroundColorParentEl?.textContent === commonAncestor.textContent) {
                    // As long as we handle the same text content, we extend the
                    // existing range to the `<font/>` boundaries to keep the
                    // background color applied correctly.
                    range.setStartBefore(backgroundColorParentEl);
                    range.setEndAfter(backgroundColorParentEl);
                }
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
                applyTextOption($snippet[0]); // TODO remove in master, useless in standard
                this.trigger_up('activate_snippet', {
                    $snippet: $snippet,
                    previewMode: false,
                    onSuccess: () => {
                        if (__handleTextOptionsPostActivate) {
                            __handleTextOptionsPostActivate($snippet);
                        }
                    },
                });
                this.options.wysiwyg.odooEditor.historyStep();
            } else {
                this.notification.add(
                    _t("Cannot apply this option on current text selection. Try clearing the format and try again."),
                    { type: 'danger', sticky: true }
                );
            }
        }
    },
    /**
     * @private
     * @param {HTMLElement} targetEl
     */
    _disableTextOptions(targetEl) {
        if (targetEl.classList.contains('o_we_animate_text')) {
            this._toggleHighlightAnimatedTextButton();
        }
        targetEl.classList.remove('active');
    },
    /**
     * Used to adjust the highlight effect when the text content is edited.
     *
     * TODO: Should be directly replaced by `switchTextHighlight()` in master
     * (left in stable for compatibility).
     *
     * @private
     * @param {HTMLElement} target
     * @param {String} [highlightID]
     */
    _adaptHighlightOnEdit(target, highlightID) {
        return switchTextHighlight(target, highlightID);
    },
    /**
     * @private
     * @param {HTMLElement} buttonEl
     */
    _getOptionTextClass(buttonEl) {
        return buttonEl.dataset.textSelector.slice(1);
    },

    /**
     * The goal here is to disable parents editors for `s_popup` snippets
     * since they should not display their parents options.
     * TODO: Update in master to set the `o_no_parent_editor` class in the
     * snippet's XML.
     *
     * @override
     */
    _allowParentsEditors($snippet) {
        return this._super(...arguments) && !$snippet[0].classList.contains("s_popup");
    },
    /**
     * @override
     */
    _updateDroppedSnippet($target) {
        // Build the highlighted text content for the snippets.
        for (const textEl of $target[0]?.querySelectorAll(".o_text_highlight") || []) {
            applyTextHighlight(textEl);
        }
        return this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onGMapAPIRequest(ev) {
        this._handleGMapRequest(ev, 'gmap_api_request');
    },
    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onGMapAPIKeyRequest(ev) {
        this._handleGMapRequest(ev, 'gmap_api_key_request');
    },
    /**
     * @private
     */
    async _onThemeTabClick(ev) {
        // Note: nothing async here but start the loading effect asap
        let releaseLoader;
        try {
            const promise = new Promise(resolve => releaseLoader = resolve);
            this._execWithLoadingEffect(() => promise, false, 0);
            // loader is added to the DOM synchronously
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            // ensure loader is rendered: first call asks for the (already done) DOM update,
            // second call happens only after rendering the first "updates"

            if (!this.topFakeOptionEl) {
                let el;
                for (const [elementName, title] of this.optionsTabStructure) {
                    const newEl = document.createElement(elementName);
                    newEl.dataset.name = title;
                    if (el) {
                        el.appendChild(newEl);
                    } else {
                        this.topFakeOptionEl = newEl;
                    }
                    el = newEl;
                }
                this.bottomFakeOptionEl = el;
                this.$body[0].appendChild(this.topFakeOptionEl);
            }

            // Need all of this in that order so that:
            // - the element is visible and can be enabled and the onFocus method is
            //   called each time.
            // - the element is hidden afterwards so it does not take space in the
            //   DOM, same as the overlay which may make a scrollbar appear.
            this.topFakeOptionEl.classList.remove('d-none');
            const editorPromise = this._activateSnippet($(this.bottomFakeOptionEl));
            releaseLoader(); // because _activateSnippet uses the same mutex as the loader
            releaseLoader = undefined;
            const editor = await editorPromise;
            this.topFakeOptionEl.classList.add('d-none');
            editor.toggleOverlay(false);

            this._updateRightPanelContent({
                tab: this.tabs.THEME,
            });
        } catch (e) {
            // Normally the loading effect is removed in case of error during the action but here
            // the actual activity is happening outside of the action, the effect must therefore
            // be cleared in case of error as well
            if (releaseLoader) {
                releaseLoader();
            }
            throw e;
        }
    },
    /**
     * @override
     */
    _onOptionsTabClick(ev) {
        if (!ev.currentTarget.classList.contains('active')) {
            this._activateSnippet(false);
            this._mutex.exec(async () => {
                const switchableViews = await new Promise((resolve, reject) => {
                    this.trigger_up('get_switchable_related_views', {
                        onSuccess: resolve,
                        onFailure: reject,
                    });
                });
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
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onAnimateTextClick(ev) {
        const target = ev.currentTarget;
        this._handleTextOptions(target, [
            this._getOptionTextClass(target),
            "o_animate",
            "o_animate_preview",
            "o_anim_fade_in"
        ]);
    },
    /**
     * @private
     */
    _onHighlightAnimatedTextClick(ev) {
        this.$body.toggleClass('o_animated_text_highlighted');
        $(ev.target).toggleClass('fa-eye fa-eye-slash').toggleClass('text-success');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onTextHighlightClick(ev) {
        // To be able to open the highlights grid immediately, we need to
        // prevent the `_onClick()` handler from closing the widget (using
        // the `_closeWidgets()` method) right after opening it.
        ev.stopPropagation();
        this._closeWidgets();
        const target = ev.currentTarget;
        this.__handleTextOptionsPostActivate = ($snippet) => {
            // TODO should be reviewed
            $snippet.data("snippet-editor")?.trigger_up("option_update", {
                optionName: "TextHighlight",
                name: "new_text_highlight",
            });
        };
        this._handleTextOptions(
            target,
            [this._getOptionTextClass(target), "o_text_highlight_underline", "o_translate_inline"],
        );
        delete this.__handleTextOptionsPostActivate;
    },
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
        const excludeSelector = this.optionsTabStructure.map(element => element[0]).join(', ');
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
    },
});

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
     * @override
     * @returns {Promise}
     */
    async updateOptionsUIVisibility() {
        await this._super(...arguments);
        // TODO improve this: some website text options (like text animations,
        // text highlights...) are moved to the toolbar, which leads to an empty
        // "options section". The goal of this override is to hide options
        // sections with no option elements.
        if (!this.$optionsSection[0].querySelector(":scope > we-customizeblock-option")) {
            this.$optionsSection[0].classList.add("d-none");
        }
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
    /**
     * TODO: Remove in master (left in stable for compatibility)
     *
     * @private
     */
    _highlightResizeObserve() {
        // The callback of `this.editorResizeObserver` will fire automatically
        // when observation starts, which triggers a useless highlight
        // adjustment. We use `this.observerLock` to prevent it.
        this.observerLock = true;
        this.editorResizeObserver.observe(this.$target[0]);
    },
    /**
     * TODO: Remove in master (left in stable for compatibility)
     *
     * @private
     */
    _adaptOnOptionResize() {
        [...this.$target[0].querySelectorAll(".o_text_highlight")].forEach(textEl => {
            switchTextHighlight(textEl);
        });
    },
});

wSnippetMenu.include({
    /**
     * @override
     */
    init: function () {
        this._super(...arguments);
        this._notActivableElementsSelector += ', .o_mega_menu_toggle';
    },
    /**
     * @override
     */
    start() {
        const _super = this._super(...arguments);
        if (this.$body[0].ownerDocument !== this.ownerDocument) {
            this.$body.on('click.snippets_menu', '*', this._onClick);
        }
        return _super;
    },
    /**
    * @override
    */
    destroy() {
        if (this.$body[0].ownerDocument !== this.ownerDocument) {
            this.$body.off('.snippets_menu');
        }
        return this._super(...arguments);
    },

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
        return this._super(...arguments).then(() => {
            for (const el of getFromEditable('.o_translation_without_style')) {
                el.classList.remove('o_translation_without_style');
                if (el.dataset.oeTranslationSaveSha) {
                    el.dataset.oeTranslationInitialSha = el.dataset.oeTranslationSaveSha;
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
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _insertDropzone: function ($hook) {
        var $hookParent = $hook.parent();
        var $dropzone = this._super(...arguments);
        $dropzone.attr('data-editor-message-default', $hookParent.attr('data-editor-message-default'));
        $dropzone.attr('data-editor-message', $hookParent.attr('data-editor-message'));
        $dropzone.attr('data-editor-sub-message', $hookParent.attr('data-editor-sub-message'));
        return $dropzone;
    },
});

export default {
    SnippetsMenu: wSnippetMenu,
};
