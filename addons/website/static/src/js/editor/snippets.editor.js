odoo.define('website.snippet.editor', function (require) {
'use strict';

const concurrency = require('web.concurrency');
const {qweb, _t, _lt} = require('web.core');
const Dialog = require('web.Dialog');
const weSnippetEditor = require('web_editor.snippet.editor');
const wSnippetOptions = require('website.editor.snippets.options');

const FontFamilyPickerUserValueWidget = wSnippetOptions.FontFamilyPickerUserValueWidget;

weSnippetEditor.Class.include({
    xmlDependencies: (weSnippetEditor.Class.prototype.xmlDependencies || [])
        .concat(['/website/static/src/xml/website.editor.xml']),
    events: _.extend({}, weSnippetEditor.Class.prototype.events, {
        'click .o_we_customize_theme_btn': '_onThemeTabClick',
    }),
    custom_events: Object.assign({}, weSnippetEditor.Class.prototype.custom_events, {
        'enabled_xml_ids_request': '_onEnabledXMLIDsRequest',
        'gmap_api_request': '_onGMapAPIRequest',
        'gmap_api_key_request': '_onGMapAPIKeyRequest',
    }),
    tabs: _.extend({}, weSnippetEditor.Class.prototype.tabs, {
        THEME: 'theme',
    }),
    optionsTabStructure: [
        ['theme-colors', _lt("Theme Colors")],
        ['theme-options', _lt("Theme Options")],
        ['website-settings', _lt("Website Settings")],
    ],

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

        return this._super(...arguments);
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
    _updateLeftPanelContent: function ({content, tab}) {
        this._super(...arguments);
        this.$('.o_we_customize_theme_btn').toggleClass('active', tab === this.tabs.THEME);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {OdooEvent} ev
     */
    _onEnabledXMLIDsRequest(ev) {
        const xmlIDs = ev.data.xmlIDs;

        // FIXME for some reason it works once and not performing any call anymore afterwards...

        (async () => {
            if (this._xmlIDsFetchingProm) {
                // If another call to _onEnabledXMLIDsRequest is done while the
                // RPC is already being performed... wait for it to be handled.
                await this._xmlIDsFetchingProm;
            }

            // Register the xml IDs status that are to be retrieved
            if (!this._xmlIDsQueue) {
                this._xmlIDsNbCalls = 0;
                this._xmlIDsQueue = [];
            }
            this._xmlIDsCall++;
            this._xmlIDsQueue.push(...xmlIDs.filter(xmlID => !!xmlID));

            // Let other potential call to _getEnabledXmlIDs be done...
            if (!this._xmlIDsMutex) {
                this._xmlIDsMutex = new concurrency.Mutex();
            }
            this._xmlIDsMutex.exec(() => concurrency.delay());
            // ... and continue each call only once all of them have registered
            // their xml ids.
            await this._xmlIDsMutex.getUnlockedDef();

            // Only for the first call make the rpc with all xml ids
            if (!this._xmlIDsFetchingProm) {
                this._xmlIDsFetchingProm = this._rpc({
                    route: '/website/theme_customize_get',
                    params: {
                        'xml_ids': this._xmlIDsQueue,
                    },
                });
            }

            // Wait for the unique rpc result for each call
            const enabledXmlIDs = await this._xmlIDsFetchingProm;

            // Once the last call of the queue received the result, start
            // accepting new calls to _onEnabledXMLIDsRequest
            if (!--this._xmlIDsNbCalls) {
                this._xmlIDsQueue = [];
                this._xmlIDsFetchingProm = null;
            }

            // Filter back on asked xml ids for this call
            ev.data.onSuccess(enabledXmlIDs.filter(xmlID => xmlIDs.includes(xmlID)));
        })();
    },
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

            this._updateLeftPanelContent({
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
});

weSnippetEditor.Editor.include({
    layoutElementsSelector: [
        weSnippetEditor.Editor.prototype.layoutElementsSelector,
        '.s_parallax_bg',
        '.o_bg_video_container',
    ].join(','),
});
});
