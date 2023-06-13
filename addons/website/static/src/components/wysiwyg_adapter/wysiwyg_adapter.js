/** @odoo-module */

import { ComponentAdapter } from 'web.OwlCompatibility';

import { useWowlService } from '@web/legacy/utils';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { setEditableWindow } from 'web_editor.utils';
import { useBus } from "@web/core/utils/hooks";

import { EditMenuDialog, MenuDialog } from "../dialog/edit_menu";
import { WebsiteDialog } from '../dialog/dialog';
import { PageOption } from "./page_options";

const { onWillStart, useEffect, onWillUnmount } = owl;

/**
 * This component adapts the Wysiwyg widget from @web_editor/wysiwyg.js.
 * It encapsulate it so that this legacy widget can work in an OWL framework.
 */
export class WysiwygAdapterComponent extends ComponentAdapter {
    /**
     * @override
     */
    setup() {
        super.setup();
        this.options = this.props.options || {};

        this.websiteService = useWowlService('website');
        this.userService = useWowlService('user');
        this.rpc = useWowlService('rpc');
        this.orm = useWowlService('orm');
        this.dialogs = useWowlService('dialog');
        this.action = useWowlService('action');

        useBus(this.websiteService.bus, 'LEAVE-EDIT-MODE', (ev) => this.leaveEditMode(ev.detail));

        this.oeStructureSelector = '#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]';
        this.oeFieldSelector = '#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])';
        this.oeCoverSelector = '#wrapwrap .s_cover[data-res-model], #wrapwrap .o_record_cover_container[data-res-model]';
        if (this.props.savableSelector) {
            this.savableSelector = this.props.savableSelector;
        } else {
            this.savableSelector = `${this.oeStructureSelector}, ${this.oeFieldSelector}, ${this.oeCoverSelector}`;
        }
        this.pageOptions = {};
        // Disable command palette since LinkTools take over that shortcut
        useHotkey('control+k', () => {});

        onWillStart(() => {
            const pageOptionEls = this.websiteService.pageDocument.querySelectorAll('.o_page_option_data');
            for (const pageOptionEl of pageOptionEls) {
                const optionName = pageOptionEl.name;
                this.pageOptions[optionName] = new PageOption(pageOptionEl, this.websiteService.pageDocument, optionName);
            }
            this.editableElements(this.$editable).addClass('o_editable');

            let switchableRelatedViews = [];
            const viewKey = this.websiteService.pageDocument.documentElement.dataset.viewXmlid;
            if (this.websiteService.isDesigner && viewKey) {
                switchableRelatedViews = this.rpc('/website/get_switchable_related_views', {key: viewKey});
            }
            // Set utils functions' editable window to the current iframe's window.
            // This allows those function to access the correct styles definitions,
            // document element, etc.
            setEditableWindow(this.websiteService.contentWindow);
            this.switchableRelatedViews = Promise.resolve(switchableRelatedViews);
        });

        useEffect(() => {
            const initWysiwyg = async () => {
                // Disable OdooEditor observer's while setting up classes
                this.widget.odooEditor.observerUnactive();
                this._addEditorMessages();
                if (this.props.beforeEditorActive) {
                    await this.props.beforeEditorActive(this.$editable);
                }
                // The jquery instance inside the iframe needs to be aware of the wysiwyg.
                this.websiteService.contentWindow.$('#wrapwrap').data('wysiwyg', this.widget);
                await new Promise((resolve, reject) => this._websiteRootEvent('widgets_start_request', {
                    editableMode: true,
                    onSuccess: resolve,
                    onFailure: reject,
                }));
                if (this.props.snippetSelector) {
                    const $snippetEl = $(this.websiteService.pageDocument).find(this.props.snippetSelector);
                    await this.widget.snippetsMenu.activateSnippet($snippetEl);
                    if ($snippetEl.length) {
                        $snippetEl[0].scrollIntoView();
                    }
                }
                this.props.wysiwygReady();
                // Wait for widgets to be destroyed and restarted before setting
                // the dirty observer (not to be confused with odooEditor
                // observer) as the widgets might trigger DOM mutations.
                this._setObserver();
                this.widget.odooEditor.observerActive();
            };

            initWysiwyg();
        }, () => []);

        useEffect(() => {
            // Back navigation is handled with an additional state in the
            // history, used to capture the popstate event.
            history.pushState(null, '');
            let hasFakeState = true;
            const leaveOnBackNavigation = () => {
                hasFakeState = false;
                this.leaveEditMode({
                    onStay: () => {
                        history.pushState(null, '');
                        hasFakeState = true;
                    },
                    onLeave: () => history.back(),
                    reloadIframe: false
                });
            };
            window.addEventListener('popstate', leaveOnBackNavigation);
            return () => {
                window.removeEventListener('popstate', leaveOnBackNavigation);
                if (hasFakeState) {
                    history.back();
                }
            };
        }, () => []);

        onWillUnmount(() => {
            if (this.dummyWidgetEl) {
                this.dummyWidgetEl.remove();
                document.body.classList.remove('editor_has_dummy_snippets');
                setEditableWindow(window);
            }
        });
    }
    /**
     * @override
     */
    onWillStart() {
        this.props.removeWelcomeMessage();
        return super.onWillStart();
    }
    /**
     * Stop the widgets and save the content.
     *
     * @returns {Promise} the save promise from the Wysiwyg widget.
     */
    async save() {
        const mainObject = this.websiteService.currentWebsite.metadata.mainObject;
        if (this.observer) {
            this.observer.disconnect();
            delete this.observer;
        }
        const dirtyPageOptions = Object.entries(this.pageOptions).filter(([name, option]) => option.isDirty);
        await Promise.all(dirtyPageOptions.map(async ([name, option]) => {
            await this.orm.write(mainObject.model, [mainObject.id], {[name]: option.value});
        }));
        return this.widget.saveContent(false);
    }
    /**
     * Returns the elements on the page which are editable.
     *
     * @param $wrapwrap
     * @returns {*}
     */
    editableElements($wrapwrap) {
        if (this.props.editableElements) {
            return this.props.editableElements();
        }
        return $wrapwrap.find('[data-oe-model]')
            .not('.o_not_editable')
            .filter(function () {
                var $parent = $(this).closest('.o_editable, .o_not_editable');
                return !$parent.length || $parent.hasClass('o_editable');
            })
            .not('link, script')
            .not('[data-oe-readonly]')
            .not('img[data-oe-field="arch"], br[data-oe-field="arch"], input[data-oe-field="arch"]')
            .not('.oe_snippet_editor')
            .not('hr, br, input, textarea')
            .not('[data-oe-sanitize-prevent-edition]')
            .add('.o_editable');
    }
    /**
     * @override
     */
    get widgetArgs() {
        return [this._wysiwygParams];
    }
    /**
     * Return the editable parent element. This includes content inside it which isn't editable.
     *
     * @returns {HTMLElement}
     */
    get editable() {
        return this.websiteService.pageDocument.getElementById('wrapwrap');
    }
    /**
     * @see {editable} jQuery wrapped editable.
     *
     * @returns {jQuery}
     */
    get $editable() {
        return $(this.editable);
    }
    get _context() {
        return Object.assign({},
            this.userService.context,
            {
                website_id: this.websiteService.currentWebsite.id,
                lang: this.websiteService.currentWebsite.metadata.lang,
                user_lang: this.userService.context.lang,
            },
        );
    }
    leaveEditMode({ onLeave, forceLeave, onStay, reloadIframe = true } = {}) {
        const leave = () => {
            this.dummyWidgetEl = this._getDummmySnippetsEl();
            this.widget.el.parentElement.appendChild(this.dummyWidgetEl);
            document.body.classList.add('editor_has_dummy_snippets');
            // The wysiwyg is destroyed to avoid listeners from the OdooEditor
            // and the SnippetsMenu to be triggered when reloading the iframe.
            this.widget.destroy();
            this.props.quitCallback({ onLeave, reloadIframe });
        };

        if (!forceLeave && this._isDirty()) {
            let leaving = false;
            // The onStay/leave callbacks are not passed directly as
            // primaryClick/secondaryClick props, so that closing the dialog
            // with "esc" or the top right cross icon also executes onStay.
            this.dialogs.add(WebsiteDialog, {
                body: this.env._t("If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."),
                primaryClick: () => leaving = true,
            }, {
                onClose: () => {
                    if (leaving) {
                        leave();
                    } else if (onStay) {
                        onStay();
                    }
                }
            });
        } else {
            leave();
        }
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Object} Params to pass to the wysiwyg widget.
     */
    get _wysiwygParams() {
        const powerboxItems = this._getSnippetsPowerboxItems();
        return {
            snippets: 'website.snippets',
            recordInfo: {
                context: this._context,
                data_res_model: 'website',
                data_res_id: this._context.website_id,
            },
            context: this._context,
            editable: this.$editable,
            discardButton: true,
            saveButton: true,
            devicePreview: true,
            savableSelector: this.savableSelector,
            isRootEditable: false,
            controlHistoryFromDocument: true,
            getContentEditableAreas: this._getContentEditableAreas.bind(this),
            document: this.websiteService.pageDocument,
            sideAttach: true,
            isWebsite: true, // If set to true, it will trigger isolated behaviours in website patches. (.include)
            powerboxCommands: powerboxItems[0],
            powerboxCategories: powerboxItems[1],
            bindLinkTool: true,
            showEmptyElementHint: false,
            getReadOnlyAreas: this._getReadOnlyAreas.bind(this),
            getUnremovableElements: this._getUnremovableElements.bind(this),
            direction: this.websiteService.currentWebsite.metadata.direction,
            ...this.props.wysiwygOptions,
        };
    }
    /**
     * Sets the observer so that if any change happen to the body and such
     * changes should be saved, the class 'o_dirty' is added to elements
     * that were changed.
     *
     * @private
     */
    _setObserver() {
        const processRecords = (records) => {
            records = this.widget.odooEditor.filterMutationRecords(records);
            // Skip the step for this stack because if the editor undo the first
            // step that has a dirty element, the following code would have
            // generated a new stack and break the "redo" of the editor.
            this.widget.odooEditor.automaticStepSkipStack();
            for (const record of records) {
                const $savable = $(record.target).closest(this.savableSelector);

                if (record.attributeName === 'contenteditable') {
                    continue;
                }
                $savable.not('.o_dirty').each(function () {
                    if (!this.hasAttribute('data-oe-readonly')) {
                        this.classList.add('o_dirty');
                    }
                });
            }
        };
        this.observer = new MutationObserver(processRecords);

        this._observe();

        this.widget.odooEditor.addEventListener('observerUnactive', () => {
            if (this.observer) {
                processRecords(this.observer.takeRecords());
                this.observer.disconnect();
            }
        });
        this.widget.odooEditor.addEventListener('observerActive', this._observe.bind(this));
    }
    /**
     * @private
     */
     _observe() {
        if (this.observer) {
            this.observer.observe(this.websiteService.pageDocument.body, {
                childList: true,
                subtree: true,
                attributes: true,
                attributeOldValue: true,
                characterData: true,
            });
        }
    }
    /**
     * Adds automatic editor messages on drag&drop zone elements.
     *
     * @private
     */
    _addEditorMessages() {
        const $wrap = this.$editable
            .find('.oe_structure.oe_empty, [data-oe-type="html"]')
            .filter(':o_editable');
        this.$editorMessageElement = $wrap.not('[data-editor-message]')
                .attr('data-editor-message-default', true)
                .attr('data-editor-message', this.env._t('DRAG BUILDING BLOCKS HERE'));
        $wrap.filter(':empty').attr('contenteditable', false);
    }
    /**
     * Get the areas on the page that should be editable.
     *
     * @returns {Node[]} list of nodes that can be edited.
     */
    _getContentEditableAreas() {
        const $savableZones = $(this.websiteService.pageDocument).find(this.savableSelector);
        const $editableSavableZones = $savableZones
            .not('input, [data-oe-readonly], ' +
                 '[data-oe-type="monetary"], [data-oe-many2one-id], [data-oe-field="arch"]:empty')
            .filter((_, el) => {
                return !$(el).closest('.o_not_editable').length;
            });

        // TODO review in master. This stable fix restores the possibility to
        // edit the company team snippet images on subsequent editions. Indeed
        // this badly relies on the contenteditable="true" attribute being on
        // those images but it is rightfully lost after the first save.
        // grep: COMPANY_TEAM_CONTENTEDITABLE
        let $extraEditableZones = $editableSavableZones.find('.s_company_team .o_not_editable img');

        // To make sure the selection remains bounded to the active tab,
        // each tab is made non editable while keeping its nested
        // oe_structure editable. This avoids having a selection range span
        // over all further inactive tabs when using Chrome.
        // grep: .s_tabs
        $extraEditableZones = $extraEditableZones.add($editableSavableZones.find('.tab-pane > .oe_structure'));

        return $editableSavableZones.add($extraEditableZones).toArray();
    }
    _getReadOnlyAreas() {
        // To make sure the selection remains bounded to the active tab,
        // each tab is made non editable while keeping its nested
        // oe_structure editable. This avoids having a selection range span
        // over all further inactive tabs when using Chrome.
        // grep: .s_tabs
        const doc = this.websiteService.pageDocument;
        return [...doc.querySelectorAll('.tab-pane > .oe_structure')].map(el => el.parentNode);
    }
    _getUnremovableElements () {
        // TODO adapt in master: this was added as a fix to target some elements
        // to be unremovable. This fix had to be reverted but to keep things
        // stable, this still had to return the same thing: a NodeList. This
        // code here seems the only (?) way to create a static empty NodeList.
        // In master, this should return an array as it seems intended by the
        // library caller anyway.
        return document.querySelectorAll('.a:not(.a)');
    }
    /**
     * This method provides support for the legacy event system.
     * The supported events are defined in the prototype.
     * @see WysiwygAdapterComponent.events
     * If the event is not supported it uses the super class method's.
     * See {@link ComponentAdapter._trigger_up}.
     *
     * @override
     * @param {Event} event
     */
    _trigger_up(event) {
        if (this.events[event.name]) {
            let method = this.events[event.name];
            return this[method](event);
        }
        return super._trigger_up(...arguments);
    }
    /***
     * Handles action request from inner widgets
     *
     * @param {Event} event the event that triggerd the action.
     * @returns {*}
     * @private
     */
    async _handleAction(event) {
        const actionName = event.data.actionName;
        const params = event.data.params;
        switch (actionName) {
            case 'get_page_option':
                 return event.data.onSuccess(this.pageOptions[params[0]].value);
            case 'toggle_page_option':
                this._togglePageOption(...params);
                return event.data.onSuccess();
            case 'edit_menu':
                return this.dialogs.add(EditMenuDialog, {
                    rootID: params[0],
                    save: () => {
                        const snippetsMenu = this.widget.snippetsMenu;
                        snippetsMenu.trigger_up('request_save', {reload: true, _toMutex: true});
                    },
                });
        }
    }
    /**
     * Toggles or force an option linked to the page.
     *
     * @see {PageOption}
     * @param {Object} params
     * @param {string} params.name the name of the page option,
     * @param {*} params.value the value if needed to be forced
     * @private
     */
    _togglePageOption(params) {
        const pageOption = this.pageOptions[params.name];
        pageOption.value = params.value === undefined ? !pageOption.value : params.value;
    }
    /**
     * Triggers an event on the iframe's public root.
     *
     * @private
     * @param type {string}
     * @param eventData {*}
     * @returns {void|OdooEvent|*}
     */
    _websiteRootEvent(type, eventData = {}) {
        const websiteRootInstance = this.websiteService.websiteRootInstance;
        // If the websiteRootInstance is gone but an event still tries to reach it
        // prevent a traceback by denying the event.
        // TODO we should investigate if this is normal the websiteRootInstance
        // is being accessed while being dead following a wysiwyg adapter event.
        if (!websiteRootInstance) {
            if (eventData.onFailure) {
                return eventData.onFailure();
            }
            return false;
        }
        return websiteRootInstance.trigger_up(type, {...eventData});
    }
    _preventDefault(e) {
        // TODO: Remove this method in master.
        e.preventDefault();
    }
    /**
     * @private
     */
     async _reloadBundles(event) {
        const bundles = await this.rpc('/website/theme_customize_bundle_reload');
        let $allLinksIframe = $();
        const proms = [];
        const createLinksProms = (bundleURLs, $insertionEl) => {
            let $newLinks = $();
            for (const url of bundleURLs) {
                $newLinks = $newLinks.add('<link/>', {
                    type: 'text/css',
                    rel: 'stylesheet',
                    href: url + `#t=${new Date().getTime()}`, // Insures that the css will be reloaded.
                });
            }
            proms.push(new Promise((resolve, reject) => {
                let nbLoaded = 0;
                $newLinks.on('load error', () => {
                    if (++nbLoaded >= $newLinks.length) {
                        resolve();
                    }
                });
            }));
            $insertionEl.after($newLinks);
        };
        _.map(bundles, (bundleURLs, bundleName) => {
            const selector = `link[href*="${bundleName}"]`;
            const $linksIframe = this.websiteService.contentWindow.$(selector);
            if ($linksIframe.length) {
                $allLinksIframe = $allLinksIframe.add($linksIframe);
                createLinksProms(bundleURLs, $linksIframe.last());
            }
        });
        await Promise.all(proms).then(() => {
            $allLinksIframe.remove();
        });
        if (event.data.onSuccess) {
            return event.data.onSuccess();
        }
    }
    /**
     * Returns the snippets commands for the powerbox
     *
     * @private
     */
    _getSnippetsPowerboxItems() {
        const snippetCommandCallback = (selector) => {
            const $separatorBody = $(selector);
            const $clonedBody = $separatorBody.clone().removeClass('oe_snippet_body');
            const range = this.widget.getDeepRange();
            const block = this.widget.closestElement(range.endContainer, 'p, div, ol, ul, cl, h1, h2, h3, h4, h5, h6');
            if (block) {
                block.after($clonedBody[0]);
                this.widget.snippetsMenu.callPostSnippetDrop($clonedBody);
            }
        };
        const commands = [
            {
                category: this.env._t('Website'),
                name: this.env._t('Alert'),
                priority: 100,
                description: this.env._t('Insert an alert snippet.'),
                fontawesome: 'fa-info',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_alert"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Rating'),
                priority: 90,
                description: this.env._t('Insert a rating snippet.'),
                fontawesome: 'fa-star-half-o',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_rating"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Card'),
                priority: 80,
                description: this.env._t('Insert a card snippet.'),
                fontawesome: 'fa-sticky-note',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_card"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Share'),
                priority: 70,
                description: this.env._t('Insert a share snippet.'),
                fontawesome: 'fa-share-square-o',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_share"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Text Highlight'),
                priority: 60,
                description: this.env._t('Insert a text Highlight snippet.'),
                fontawesome: 'fa-sticky-note',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_text_highlight"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Chart'),
                priority: 50,
                description: this.env._t('Insert a chart snippet.'),
                fontawesome: 'fa-bar-chart',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_chart"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Progress Bar'),
                priority: 40,
                description: this.env._t('Insert a progress bar snippet.'),
                fontawesome: 'fa-spinner',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_progress_bar"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Badge'),
                priority: 30,
                description: this.env._t('Insert a badge snippet.'),
                fontawesome: 'fa-tags',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_badge"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Blockquote'),
                priority: 20,
                description: this.env._t('Insert a blockquote snippet.'),
                fontawesome: 'fa-quote-left',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_blockquote"]');
                },
            },
            {
                category: this.env._t('Website'),
                name: this.env._t('Separator'),
                priority: 10,
                description: this.env._t('Insert an horizontal separator sippet.'),
                fontawesome: 'fa-minus',
                isDisabled: () => !this.widget.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_hr"]');
                },
            },
        ];
        return [commands, [{ name: 'Website', priority: 20 }]];
    }
    /**
     * @returns {boolean} true if the page has been altered.
     */
    _isDirty() {
        return this.widget.isDirty() || Object.values(this.pageOptions).some(option => option.isDirty);
    }

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * Creates a new event and dispatch it in the iframe's public widget
     *
     * @param {OdooEvent} event
     * @private
     */
    _onRootEventRequest(event) {
        return this._websiteRootEvent(event.name, event.data);
    }

    /**
     * Saves the editables to the server if it's dirty. If no
     * callbacks are given, leaves the editor, otherwise, perform
     * the callback.
     *
     * @param event
     * @param [event.data.onSuccess] {Function} Async callback
     * @param [event.data.reload] {boolean}
     * @param [event.data.reloadEditor] {boolean} reloads the editor.
     * @param [event.data.reloadWebClient] reloads the Webclient.
     * @returns {Promise<unknown>}
     * @private
     */
    async _onSaveRequest(event) {
        let callback = () => this.leaveEditMode({ forceLeave: true });
        if (event.data.reload || event.data.reloadEditor) {
            this.widget.trigger_up('disable_loading_effects');
            this.props.willReload(this._getDummmySnippetsEl());
            callback = async () => {
                if (event.data.onSuccess) {
                    await event.data.onSuccess();
                }
                return this.props.reloadCallback({
                    snippetOptionSelector: event.data.optionSelector,
                    url: event.data.url,
                    invalidateSnippetCache: event.data.invalidateSnippetCache
                });
            };
        } else if (event.data.onSuccess) {
            callback = event.data.onSuccess;
        } else if (event.data.reloadWebClient) {
            const currentPath = encodeURIComponent(window.location.pathname);
            const websiteId = this.websiteService.currentWebsite.id;
            callback = () => window.location = `/web#action=website.website_preview&website_id=${encodeURIComponent(websiteId)}&path=${currentPath}&enable_editor=1`;
        } else if (event.data.action) {
            callback = () => {
                this.leaveEditMode({
                    onLeave: () => this.action.doAction(event.data.action),
                    forceLeave: true,
                    reloadIframe: false,
                });
            };
        }
        if (this._isDirty()) {
            return this.save().then(callback, event.data.onFailure);
        } else {
            return callback();
        }
    }
    /**
     * Returns the user context.
     * @link {@web/core/user_service.js}
     *
     * @param event
     * @returns {*}
     * @private
     */
    _onContextGet(event) {
        return event.data.callback(this._context);
    }
    /**
     * Retrieves the website service context.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onServiceContextGet(ev) {
        ev.data.callback({
            isMobile: this.websiteService.context.isMobile,
        });
    }
    /**
     * Discards changes and reload the iframe.
     *
     * @param event
     * @returns {*}
     * @private
     */
    _onCancelRequest(event) {
        this.leaveEditMode({ onStay: event.data.onReject });
    }
    /**
     * Called when a snippet is about to be cloned in the page. Notifies the
     * WebsiteRoot that it should stop the public widgets inside that snippet.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetWillBeCloned(ev) {
        this._websiteRootEvent('widgets_stop_request', {
            $target: ev.data.$target,
        });
    }
    /**
     * Called when a snippet is cloned in the page. Notifies the WebsiteRoot
     * that it should start the public widgets for this snippet and the snippet it
     * was cloned from.
     *
     * @private
     * @param {OdooEvent} ev
     */
    _onSnippetCloned(ev) {
        this._websiteRootEvent('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$target,
        });

        this._websiteRootEvent('widgets_start_request', {
            editableMode: true,
            $target: ev.data.$origin,
        });
    }
    /***
     * Starts the widgets inside the dropped snippet.
     *
     * @param event {Object}
     * @param event.data.addPostDropAsync {Function} Function used to push a promise in the stack.
     * @see web_editor/SnippetsMenu.callPostSnippetDrop
     * @private
     */
    _onSnippetDropped(event) {
        event.data.addPostDropAsync(new Promise(resolve => {
            this._websiteRootEvent('widgets_start_request', {
                editableMode: true,
                $target: event.data.$target,
                onSuccess: () => resolve(),
            });
        }));
    }
    /***
     * Re-add the editor message if no content is left on the page.
     *
     * @param event
     * @private
     */
    _onSnippetRemoved(event) {
        const $empty = this.$editable.find('.oe_empty');
        if (!$empty.children().length) {
            $empty.empty(); // Remove any superfluous whitespace
            this._addEditorMessages();
        }
    }
    /**
     * Adds / Edit an entry in the website menu.
     *
     * @param event
     * @private
     */
    _onMenuDialogRequest(event) {
        this.dialogs.add(MenuDialog, {
            name: event.data.name,
            url: event.data.url,
            isMegaMenu: event.data.isMegaMenu,
            save: async (...args) => {
                await event.data.save(...args);
            },
        });
    }
    /**
     * Updates the panel so that color previews reflects the ones used by the
     * edited content.
     *
     * @private
     */
    _onColorPreviewsUpdate() {
        this.widget.setCSSVariables(this.widget.snippetsMenu.el);
    }
    /**
     * Update the context to trigger a mobile view.
     * @private
     */
    _onMobilePreviewRequest() {
        this.websiteService.context.isMobile = !this.websiteService.context.isMobile;
    }
    /**
     * Called when a child needs to know about the views that can
     * be toggled on or off on a specific view related to the editable.
     *
     * @param event
     * @returns {Promise<void>}
     * @private
     */
    async _onGetSwitchableRelatedViews(event) {
        const views = await this.switchableRelatedViews;
        event.data.onSuccess(views);
    }
    /**
     * This method returns a visual skeleton of the snippets menu, by making a
     * copy of the Wysiwyg element. This is used when reloading the iframe or
     * leaving the edit mode, so that the widget can be destroyed under the
     * hood (ideally, the Wysiwyg would remove its listeners on the document,
     * so that they are not triggered during a reload).
     */
    _getDummmySnippetsEl() {
        const dummySnippetsEl = this.widget.el.cloneNode(true);
        dummySnippetsEl.querySelectorAll('#oe_manipulators, .d-none, .oe_snippet_body').forEach(el => el.remove());
        dummySnippetsEl.querySelectorAll('we-input input').forEach(input => {
            input.setAttribute('value', input.closest('we-input').dataset.selectStyle || '');
        });
        return dummySnippetsEl;
    }
}
WysiwygAdapterComponent.prototype.events = {
    'widgets_start_request': '_onRootEventRequest',
    'widgets_stop_request': '_onRootEventRequest',
    'ready_to_clean_for_save': '_onRootEventRequest',
    'will_remove_snippet': '_onRootEventRequest',
    'gmap_api_request': '_onRootEventRequest',
    'gmap_api_key_request': '_onRootEventRequest',
    'request_save': '_onSaveRequest',
    'context_get': '_onContextGet',
    'service_context_get': '_onServiceContextGet',
    'action_demand': '_handleAction',
    'request_cancel': '_onCancelRequest',
    'snippet_will_be_cloned': '_onSnippetWillBeCloned',
    'snippet_cloned': '_onSnippetCloned',
    'snippet_dropped': '_onSnippetDropped',
    'snippet_removed': '_onSnippetRemoved',
    'reload_bundles': '_reloadBundles',
    'menu_dialog': '_onMenuDialogRequest',
    'update_color_previews': '_onColorPreviewsUpdate',
    'request_mobile_preview': '_onMobilePreviewRequest',
    'get_switchable_related_views': '_onGetSwitchableRelatedViews',
};
