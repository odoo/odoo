/** @odoo-modules **/

import { _t } from "@web/core/l10n/translation";
import Dialog from "@web/legacy/js/core/dialog";
import weSnippetEditor from "@web_editor/js/editor/snippets.editor";
import wSnippetOptions from "@website/js/editor/snippets.options";
import * as OdooEditorLib from "@web_editor/js/editor/odoo-editor/src/utils/utils";
import { renderToElement } from "@web/core/utils/render";
const getDeepRange = OdooEditorLib.getDeepRange;
const getTraversedNodes = OdooEditorLib.getTraversedNodes;

const FontFamilyPickerUserValueWidget = wSnippetOptions.FontFamilyPickerUserValueWidget;

const wSnippetMenu = weSnippetEditor.SnippetsMenu.extend({
    events: Object.assign({}, weSnippetEditor.SnippetsMenu.prototype.events, {
        'click .o_we_customize_theme_btn': '_onThemeTabClick',
        'click .o_we_animate_text': '_onAnimateTextClick',
        'click .o_we_highlight_animated_text': '_onHighlightAnimatedTextClick',
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
    async start() {
        await this._super(...arguments);

        this.__onSelectionChange = ev => {
            this._toggleAnimatedTextButton();
        };
        this.$body[0].ownerDocument.addEventListener('selectionchange', this.__onSelectionChange);

        // editor_has_snippets is, amongst other things, in charge of hiding the
        // backend navbar with a CSS animation. But we also need to make it
        // display: none when the animation finishes for efficiency but also so
        // that the tour tooltips pointing at the navbar disappear. This could
        // rely on listening to the transitionend event but it seems more future
        // proof to just add a delay after which the navbar is hidden.
        this._hideBackendNavbarTimeout = setTimeout(() => {
            this.el.ownerDocument.body.classList.add('editor_has_snippets_hide_backend_navbar');
        }, 500);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.$body[0].ownerDocument.removeEventListener('selectionchange', this.__onSelectionChange);
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

        const $content = $(renderToElement('website.s_google_map_modal', {
            apiKey: apiKey,
        }));
        if (!apiKeyValidation.isValid && apiKeyValidation.message) {
            applyError.call($content, apiKeyValidation.message);
        }

        return new Promise(resolve => {
            let invalidated = false;
            const dialog = new Dialog(this, {
                size: 'medium',
                title: _t("Google Map API Key"),
                buttons: [
                    {text: _t("Save"), classes: 'btn-primary', click: async (ev) => {
                        const valueAPIKey = dialog.$('#api_key_input').val();
                        if (!valueAPIKey) {
                            applyError.call(dialog.$el, _t("Enter an API Key"));
                            return;
                        }
                        const $button = $(ev.currentTarget);
                        $button.prop('disabled', true);
                        const res = await this._validateGMapAPIKey(valueAPIKey);
                        if (res.isValid) {
                            await this.orm.write("website", [websiteId], { google_maps_api_key: valueAPIKey });
                            invalidated = true;
                            dialog.close();
                        } else {
                            applyError.call(dialog.$el, res.message);
                        }
                        $button.prop("disabled", false);
                    }},
                    {text: _t("Cancel"), close: true}
                ],
                $content: $content,
            });
            dialog.on('closed', this, () => resolve(invalidated));
            dialog.open();
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
    _getScrollOptions(options = {}) {
        const finalOptions = this._super(...arguments);
        if (!options.offsetElements || !options.offsetElements.$top) {
            const $header = $('#top');
            if ($header.length) {
                finalOptions.offsetElements = finalOptions.offsetElements || {};
                finalOptions.offsetElements.$top = $header;
            }
        }
        finalOptions.jQueryDraggableOptions.iframeFix = true;
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
     * Returns the animated text element wrapping the selection if it exists.
     *
     * @private
     * @return {Element|false}
     */
    _getAnimatedTextElement() {
        const editable = this.options.wysiwyg.$editable[0];
        const animatedTextNode = getTraversedNodes(editable).find(n => n.parentElement.closest(".o_animated_text"));
        return animatedTextNode ? animatedTextNode.parentElement.closest('.o_animated_text') : false;
    },
    /**
     * @override
     */
    _addToolbar() {
        this._super(...arguments);
        this.$('#o_we_editor_toolbar_container > we-title > span').after($(`
            <div class="btn fa fa-fw fa-2x o_we_highlight_animated_text d-none
                ${this.$body.hasClass('o_animated_text_highlighted') ? 'fa-eye text-success' : 'fa-eye-slash'}"
                title="${_t('Highlight Animated Text')}"
                aria-label="Highlight Animated Text"/>
        `));
        this._toggleAnimatedTextButton();
        this._toggleHighlightAnimatedTextButton();
    },
    /**
     * Activates the button to animate text if the selection is in an
     * animated text element or deactivates the button if not.
     *
     * @private
     */
    _toggleAnimatedTextButton() {
        const sel = this.options.wysiwyg.odooEditor.document.getSelection();
        if (!this._isValidSelection(sel)) {
            return;
        }
        const animatedText = this._getAnimatedTextElement();
        this.$('.o_we_animate_text').toggleClass('active', !!animatedText);
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
     */
    _onAnimateTextClick(ev) {
        const sel = this.options.wysiwyg.odooEditor.document.getSelection();
        if (!this._isValidSelection(sel)) {
            return;
        }
        const editable = this.options.wysiwyg.$editable[0];
        const range = getDeepRange(editable, { splitText: true, select: true, correctTripleClick: true });
        const animatedText = this._getAnimatedTextElement();
        if (animatedText) {
            $(animatedText).contents().unwrap();
            this.options.wysiwyg.odooEditor.historyResetLatestComputedSelection();
            this._toggleHighlightAnimatedTextButton();
            ev.target.classList.remove('active');
            this.options.wysiwyg.odooEditor.historyStep();
        } else {
            if (sel.getRangeAt(0).collapsed) {
                return;
            }
            const animatedTextEl = document.createElement('span');
            animatedTextEl.classList.add('o_animated_text', 'o_animate', 'o_animate_preview', 'o_anim_fade_in');
            let $snippet = null;
            try {
                range.surroundContents(animatedTextEl);
                $snippet = $(animatedTextEl);
            } catch {
                // This try catch is needed because 'surroundContents' may
                // fail when the range has partially selected a non-Text node.
                if (range.commonAncestorContainer.textContent === range.toString()) {
                    const $commonAncestor = $(range.commonAncestorContainer);
                    $commonAncestor.wrapInner(animatedTextEl);
                    $snippet = $commonAncestor.find('.o_animated_text');
                }
            }
            if ($snippet) {
                $snippet[0].normalize();
                this.trigger_up('activate_snippet', {
                    $snippet: $snippet,
                    previewMode: false,
                });
                this.options.wysiwyg.odooEditor.historyStep();
            } else {
                this.displayNotification({
                    message: _t("The current text selection cannot be animated. Try clearing the format and try again."),
                    type: 'danger',
                    sticky: true,
                });
            }
        }
    },
    /**
     * @private
     */
    _onHighlightAnimatedTextClick(ev) {
        this.$body.toggleClass('o_animated_text_highlighted');
        $(ev.target).toggleClass('fa-eye fa-eye-slash').toggleClass('text-success');
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
        if (this.options.enableTranslation) {
            return _super;
        }
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
