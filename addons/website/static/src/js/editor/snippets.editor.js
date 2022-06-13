odoo.define('website.snippet.editor', function (require) {
'use strict';

const {qweb, _t, _lt} = require('web.core');
const Dialog = require('web.Dialog');
const weSnippetEditor = require('web_editor.snippet.editor');
const wSnippetOptions = require('website.editor.snippets.options');
const OdooEditorLib = require('@web_editor/../lib/odoo-editor/src/utils/utils');
const getDeepRange = OdooEditorLib.getDeepRange;
const getTraversedNodes = OdooEditorLib.getTraversedNodes;

const FontFamilyPickerUserValueWidget = wSnippetOptions.FontFamilyPickerUserValueWidget;

weSnippetEditor.SnippetsMenu.include({
    xmlDependencies: (weSnippetEditor.SnippetsMenu.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),
    events: _.extend({}, weSnippetEditor.SnippetsMenu.prototype.events, {
        'click .o_we_customize_theme_btn': '_onThemeTabClick',
        'click .o_we_animate_text': '_onAnimateTextClick',
        'click .o_we_highlight_animated_text': '_onHighlightAnimatedTextClick',
    }),
    custom_events: Object.assign({}, weSnippetEditor.SnippetsMenu.prototype.custom_events, {
        'gmap_api_request': '_onGMapAPIRequest',
        'gmap_api_key_request': '_onGMapAPIKeyRequest',
    }),
    tabs: _.extend({}, weSnippetEditor.SnippetsMenu.prototype.tabs, {
        THEME: 'theme',
    }),
    optionsTabStructure: [
        ['theme-colors', _lt("Theme Colors")],
        ['theme-options', _lt("Theme Options")],
        ['website-settings', _lt("Website Settings")],
    ],

    /**
     * @override
     */
    async start() {
        await this._super(...arguments);
        this.$currentAnimatedText = $();

        this.__onSelectionChange = ev => {
            this._toggleAnimatedTextButton();
        };
        this.ownerDocument.addEventListener('selectionchange', this.__onSelectionChange);
    },
    /**
     * @override
     */
    destroy() {
        this._super(...arguments);
        this.ownerDocument.removeEventListener('selectionchange', this.__onSelectionChange);
        document.body.classList.remove('o_animated_text_highlighted');
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeSnippetTemplates: function (html) {
        const $html = $(html);
        const fontVariables = _.map($html.find('we-fontfamilypicker[data-variable]'), el => {
            return el.dataset.variable;
        });
        FontFamilyPickerUserValueWidget.prototype.fontVariables = fontVariables;

        const ret = this._super(...arguments);

        // TODO adapt in master. This patches the embed code snippet
        // in stable versions.
        const $sbody = this.$snippets.find('[data-snippet="s_embed_code"]');
        if ($sbody.length) {
            $sbody[0].classList.remove('o_half_screen_height');
            $sbody[0].classList.add('pt64', 'pb64');
        }

        return ret;
    },
    /**
     * Depending of the demand, reconfigure they gmap key or configure it
     * if not already defined.
     *
     * @private
     * @param {boolean} [reconfigure=false]
     * @param {boolean} [onlyIfUndefined=false]
     */
    async _configureGMapAPI({reconfigure, onlyIfUndefined}) {
        const apiKey = await new Promise(resolve => {
            this.getParent().trigger_up('gmap_api_key_request', {
                onSuccess: key => resolve(key),
            });
        });
        if (!reconfigure && (apiKey || !onlyIfUndefined)) {
            return false;
        }
        let websiteId;
        this.trigger_up('context_get', {
            callback: ctx => websiteId = ctx['website_id'],
        });
        return new Promise(resolve => {
            let invalidated = false;
            const dialog = new Dialog(this, {
                size: 'medium',
                title: _t("Google Map API Key"),
                buttons: [
                    {text: _t("Save"), classes: 'btn-primary', click: async (ev) => {
                        const $apiKeyInput = dialog.$('#api_key_input');
                        const valueAPIKey = $apiKeyInput.val();
                        const $apiKeyHelp = dialog.$('#api_key_help');
                        if (!valueAPIKey) {
                            $apiKeyInput.addClass('is-invalid');
                            $apiKeyHelp.text(_t("Enter an API Key"));
                            return;
                        }
                        const $button = $(ev.currentTarget);
                        $button.prop('disabled', true);
                        try {
                            const response = await fetch(`https://maps.googleapis.com/maps/api/staticmap?center=belgium&size=10x10&key=${valueAPIKey}`);
                            if (response.status === 200) {
                                await this._rpc({
                                    model: 'website',
                                    method: 'write',
                                    args: [
                                        [websiteId],
                                        {google_maps_api_key: valueAPIKey},
                                    ],
                                });
                                invalidated = true;
                                dialog.close();
                            } else {
                                const text = await response.text();
                                $apiKeyInput.addClass('is-invalid');
                                $apiKeyHelp.empty().text(
                                    _t("Invalid API Key. The following error was returned by Google:")
                                ).append($('<i/>', {
                                    text: text,
                                    class: 'ml-1',
                                }));
                            }
                        } catch (e) {
                            $apiKeyHelp.text(_t("Check your connection and try again"));
                        } finally {
                            $button.prop("disabled", false);
                        }
                    }},
                    {text: _t("Cancel"), close: true}
                ],
                $content: $(qweb.render('website.s_google_map_modal', {
                    apiKey: apiKey,
                })),
            });
            dialog.on('closed', this, () => resolve(invalidated));
            dialog.open();
        });
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
            reconfigure: ev.data.reconfigure,
            onlyIfUndefined: ev.data.configureIfNecessary,
        });
        this.getParent().trigger_up(gmapRequestEventName, {
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
                ${$('body').hasClass('o_animated_text_highlighted') ? 'fa-eye text-success' : 'fa-eye-slash'}"
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
        if (!this._isValidSelection(window.getSelection())) {
            return;
        }
        const animatedText = this._getAnimatedTextElement();
        this.$('.o_we_animate_text').toggleClass('active', !!animatedText);
        this.$currentAnimatedText = animatedText ? $(animatedText) : $();
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
                this.el.appendChild(this.topFakeOptionEl);
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
     * @private
     */
    _onAnimateTextClick(ev) {
        const sel = window.getSelection();
        if (!this._isValidSelection(sel)) {
            return;
        }
        const editable = this.options.wysiwyg.$editable[0];
        const range = getDeepRange(editable, { splitText: true, select: true, correctTripleClick: true });
        if (this.$currentAnimatedText.length) {
            this.$currentAnimatedText.contents().unwrap();
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
            } catch (e) {
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
        $('body').toggleClass('o_animated_text_highlighted');
        $(ev.target).toggleClass('fa-eye fa-eye-slash').toggleClass('text-success');
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
});
});
