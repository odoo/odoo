/** @odoo-module */

import { ComponentAdapter } from 'web.OwlCompatibility';
import { _t } from '@web/core/l10n/translation';

import { useWowlService } from '@web/legacy/utils';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { setEditableWindow } from 'web_editor.utils';

import { EditMenuDialog, MenuDialog } from "../dialog/edit_menu";
import { WebsiteDialog } from '../dialog/dialog';
import { PageOption } from "./page_options";

const { onWillStart, useEffect } = owl;

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

        this.oeStructureSelector = '#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]';
        this.oeFieldSelector = '#wrapwrap [data-oe-field]';
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
            this.switchableRelatedViews = Promise.resolve(switchableRelatedViews);
        });

        useEffect(() => {
            const initWysiwyg = async () => {
                this.$editable.on('click.odoo-website-editor', '*', this, this._preventDefault);
                // Disable OdooEditor observer's while setting up classes
                this.widget.odooEditor.observerUnactive();
                this._addEditorMessages();
                if (this.props.beforeEditorActive) {
                    await this.props.beforeEditorActive(this.$editable);
                }
                this._setObserver();

                if (this.props.snippetSelector) {
                    const $snippetEl = $(this.websiteService.pageDocument).find(this.props.snippetSelector);
                    await this.widget.snippetsMenu.activateSnippet($snippetEl);
                    if ($snippetEl.length) {
                        $snippetEl[0].scrollIntoView();
                    }
                }
                // The jquery instance inside the iframe needs to be aware of the wysiwyg.
                this.websiteService.contentWindow.$('#wrapwrap').data('wysiwyg', this.widget);
                this._websiteRootEvent('widgets_start_request', {editableMode: true, onSuccess: () => {
                    this.widget.odooEditor.observerActive();
                }});
                this.props.wysiwygReady();
                // Set utils functions' editable window to the current iframe's window.
                // This allows those function to access the correct styles definitions,
                // document element, etc.
                setEditableWindow(this.websiteService.contentWindow);
            };

            initWysiwyg();

            return () => {
                this.$editable.off('click.odoo-website-editor', '*');
                setEditableWindow(window);
            };
        }, () => []);

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
                lang: (this.websiteService.pageDocument.documentElement.getAttribute('lang') || 'en_US').replace('-', '_'),
            },
        );
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Object} Params to pass to the wysiwyg widget.
     */
    get _wysiwygParams() {
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
            powerboxCommands: this._getSnippetsCommands(),
            bindLinkTool: true,
            showEmptyElementHint: false,
            getReadOnlyAreas: this._getReadOnlyAreas.bind(this),
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
        const $wrap = this.$editable.find('.oe_structure.oe_empty, [data-oe-type="html"]');
        this.$editorMessageElement = $wrap.not('[data-editor-message]')
                .attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
        $wrap.filter(':empty').attr('contenteditable', false);
    }
    /**
     * Get the areas on the page that should be editable.
     *
     * @returns {Node[]} list of nodes that can be edited.
     */
    _getContentEditableAreas() {
        const savableElements = $(this.websiteService.pageDocument).find(this.savableSelector)
                                .not('input, [data-oe-readonly],[data-oe-type="monetary"],[data-oe-many2one-id], [data-oe-field="arch"]:empty');
        return Array.from(savableElements).filter(element => !element.closest('.o_not_editable'));
    }
    _getReadOnlyAreas() {
        return [];
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
                return this._togglePageOption(...params);
            case 'edit_menu':
                return this.dialogs.add(EditMenuDialog, {
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
        return websiteRootInstance.trigger_up(type, {...eventData});
    }
    _preventDefault(e) {
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
    _getSnippetsCommands() {
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
        return [
            {
                groupName: 'Website',
                title: 'Alert',
                description: 'Insert an alert snippet.',
                fontawesome: 'fa-info',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_alert"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Rating',
                description: 'Insert a rating snippet.',
                fontawesome: 'fa-star-half-o',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_rating"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Card',
                description: 'Insert a card snippet.',
                fontawesome: 'fa-sticky-note',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_card"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Share',
                description: 'Insert a share snippet.',
                fontawesome: 'fa-share-square-o',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_share"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Text Highlight',
                description: 'Insert a text Highlight snippet.',
                fontawesome: 'fa-sticky-note',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_text_highlight"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Chart',
                description: 'Insert a chart snippet.',
                fontawesome: 'fa-bar-chart',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_chart"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Progress Bar',
                description: 'Insert a progress bar snippet.',
                fontawesome: 'fa-spinner',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_progress_bar"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Badge',
                description: 'Insert a badge snippet.',
                fontawesome: 'fa-tags',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_badge"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Blockquote',
                description: 'Insert a blockquote snippet.',
                fontawesome: 'fa-quote-left',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_blockquote"]');
                },
            },
            {
                groupName: 'Website',
                title: 'Separator',
                description: 'Insert an horizontal separator sippet.',
                fontawesome: 'fa-minus',
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_hr"]');
                },
            },
        ];
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
        const isDirty = this.widget.isDirty();
        let callback = () => this.props.quitCallback();
        if (event.data.reload || event.data.reloadEditor) {
            this.widget.trigger_up('disable_loading_effects');
            this.props.willReload(this.widget.el);
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
            callback = () => window.location = `/web#action=website.website_preview&website_id=${websiteId}&path=${currentPath}&enable_editor=1`;
        }
        if (isDirty) {
            return this.save().then(callback);
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
     * Discards changes and reload the iframe.
     *
     * @param event
     * @returns {*}
     * @private
     */
    _onCancelRequest(event) {
        const isDirty = this.widget.isDirty();
        if (isDirty) {
            this.dialogs.add(WebsiteDialog, {
                body: _t("If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."),
                primaryClick: () => this.props.quitCallback(),
                secondaryClick: event.data.onReject,
            });
        } else {
            return this.props.quitCallback();
        }
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
    /***
     * Updates the Color Preview elements to reflect
     * the colors that are inside the iframe.
     * See the web_editor.color.combination.preview QWeb template.
     *
     * @param event
     * @param event.data.ccPreviewEls {HTMLElement} The color combination preview element.
     * @private
     */
    _onColorPreviewsUpdate(event) {
        this.widget.setCSSVariables(this.widget.snippetsMenu.el);
        const stylesToCopy = [
            'background-color',
            'border',
            'color',
        ];
        const copyStyles = (from, to) => {
            const cloneStyle = this.websiteService.contentWindow.getComputedStyle(from);
            for (const style of stylesToCopy) {
                to.style.setProperty(style, cloneStyle.getPropertyValue(style));
            }
        };

        for (const ccPreviewEl of event.data.ccPreviewEls) {
            ccPreviewEl.setAttribute('style', '');
            Object.values(ccPreviewEl.children).forEach(child => child.setAttribute('style', ''));
            const iframeClone = ccPreviewEl.cloneNode(true);
            this.websiteService.pageDocument.body.appendChild(iframeClone);
            copyStyles(iframeClone, ccPreviewEl);
            copyStyles(iframeClone.querySelector('h1'), ccPreviewEl.querySelector('h1'));
            copyStyles(iframeClone.querySelector('.btn-primary'), ccPreviewEl.querySelector('.btn-primary'));
            copyStyles(iframeClone.querySelector('.btn-secondary'), ccPreviewEl.querySelector('.btn-secondary'));
            copyStyles(iframeClone.querySelector('p'), ccPreviewEl.querySelector('p'));
            iframeClone.remove();
        }
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
}
WysiwygAdapterComponent.prototype.events = {
    'widgets_start_request': '_onRootEventRequest',
    'widgets_stop_request': '_onRootEventRequest',
    'ready_to_clean_for_save': '_onRootEventRequest',
    'gmap_api_request': '_onRootEventRequest',
    'gmap_api_key_request': '_onRootEventRequest',
    'request_save': '_onSaveRequest',
    'context_get': '_onContextGet',
    'action_demand': '_handleAction',
    'request_cancel': '_onCancelRequest',
    'snippet_dropped': '_onSnippetDropped',
    'snippet_removed': '_onSnippetRemoved',
    'reload_bundles': '_reloadBundles',
    'menu_dialog': '_onMenuDialogRequest',
    'update_color_previews': '_onColorPreviewsUpdate',
    'request_mobile_preview': '_onMobilePreviewRequest',
    'get_switchable_related_views': '_onGetSwitchableRelatedViews',
};
