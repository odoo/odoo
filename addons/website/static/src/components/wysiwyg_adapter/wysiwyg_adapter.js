/** @odoo-module */

import { ComponentAdapter } from 'web.OwlCompatibility';
import { _t } from '@web/core/l10n/translation';

import { useWowlService } from '@web/legacy/utils';

import { EditMenuDialog, MenuDialog } from "../dialog/edit_menu";
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
        const options = this.props.options || {};

        this.websiteService = useWowlService('website');
        this.userService = useWowlService('user');
        this.rpc = useWowlService('rpc');
        this.orm = useWowlService('orm');
        this.dialogs = useWowlService('dialog');

        this.oeStructureSelector = '#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]';
        this.oeFieldSelector = '#wrapwrap [data-oe-field]';
        this.oeCoverSelector = '#wrapwrap .s_cover[data-res-model], #wrapwrap .o_record_cover_container[data-res-model]';
        if (options.savableSelector) {
            this.savableSelector = options.savableSelector;
        } else {
            this.savableSelector = `${this.oeStructureSelector}, ${this.oeFieldSelector}, ${this.oeCoverSelector}`;
        }
        this.pageOptions = {};

        onWillStart(() => {
            const pageOptionEls = this.websiteService.pageDocument.querySelectorAll('.o_page_option_data');
            for (const pageOptionEl of pageOptionEls) {
                const optionName = pageOptionEl.name;
                this.pageOptions[optionName] = new PageOption(pageOptionEl, this.websiteService.pageDocument, optionName);
            }
            this.editableElements(this.$editable).addClass('o_editable');
        });

        useEffect(() => {
            const initWysiwyg = async () => {
                this.$editable.on('click.odoo-website-editor', '*', this, this._preventDefault);
                // Disable OdooEditor observer's while setting up classes
                this.widget.odooEditor.observerUnactive();
                this._addEditorMessages();
                this.widget.odooEditor.observerActive();
                this._setObserver();

                if (this.props.snippetSelector) {
                    const $snippetEl = $(this.websiteService.pageDocument).find(this.props.snippetSelector);
                    await this.widget.snippetsMenu.activateSnippet($snippetEl);
                    if ($snippetEl.length) {
                        $snippetEl[0].scrollIntoView();
                    }
                    this.websiteService.unblockIframe();
                }

                this.props.wysiwygReady();
            };

            initWysiwyg();

            return () => {
                this.$editable.off('click.odoo-website-editor', '*');
            };
        }, () => []);
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
        await this._websiteRootEvent('widgets_stop_request');
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
     * @returns {*|jQuery|HTMLElement}
     */
    get $editable() {
        return $(this.editable);
    }
    get _context() {
        return Object.assign({},
                        this.userService.context,
                        {website_id: this.websiteService.currentWebsite.id},
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
        const observe = () => {
            if (this.observer) {
                this.observer.observe(this.websiteService.pageDocument.body, {
                    childList: true,
                    subtree: true,
                    attributes: true,
                    attributeOldValue: true,
                    characterData: true,
                });
            }
        };
        observe();

        this.widget.odooEditor.addEventListener('observerUnactive', () => {
            if (this.observer) {
                processRecords(this.observer.takeRecords());
                this.observer.disconnect();
            }
        });
        this.widget.odooEditor.addEventListener('observerActive', observe);
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
    /**
     * This method provides support for the legacy event system.
     * It sends events to the root_widget in the iframe when it needs
     * to (e.g. widgets_stop_request). It also provides support for the
     * action_demand. See {@link _handleAction}.
     * If the event is not supported it uses the super class method's.
     * See {@link ComponentAdapter._trigger_up}.
     *
     * @override
     * @param {Event} event
     */
    _trigger_up(event) {
        if (this.events[event.name]) {
            let method = this.events[event.name];
            const def = this[method](event);
             if (def && def.then && event.data.onSuccess) {
                if (event.data.onFailure) {
                    def.catch(error => event.data.onFailure(error));
                }
                def.then(result => event.data.onSuccess(result));
             }
             if (event.data.callback) {
                 event.data.callback(def);
             }
             return def;
        }
        return super._trigger_up(...arguments);
    }
    /***
     * Handles action request from inner widgets
     * @param {Event} event the event that triggerd the action.
     * @returns {*}
     * @private
     */
    async _handleAction(event) {
        const actionName = event.data.actionName;
        const params = event.data.params;
        switch (actionName) {
            case 'get_page_option':
                return this.pageOptions[params[0]].value;
            case 'toggle_page_option':
                return this._togglePageOption(...params);
            case 'edit_menu':
                return this.dialogs.add(EditMenuDialog, {
                    save: () => {
                        this.props.willReload(this.widget.el.cloneNode(true));
                        this.props.reloadCallback();
                    },
                });
        }
        console.warn('action ', actionName, 'is not yet supported');
    }
    /**
     * Toggles or force an option linked to the page.
     * @see {PageOption}
     * @param {Object} params
     * @param {String} params.name the name of the page option,
     * @param {*} params.value the value if needed to be forced
     * @private
     */
    _togglePageOption(params) {
        const pageOption = this.pageOptions[params.name];
        pageOption.value = params.value === undefined ? !pageOption.value : params.value;
    }
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
     async _reloadBundles() {
        const bundles = await this._rpc({
            route: '/website/theme_customize_bundle_reload',
        });
        let $allLinks = $();
        const proms = _.map(bundles, (bundleURLs, bundleName) => {
            var $links = $('link[href*="' + bundleName + '"]');
            $allLinks = $allLinks.add($links);
            var $newLinks = $();
            _.each(bundleURLs, url => {
                $newLinks = $newLinks.add($('<link/>', {
                    type: 'text/css',
                    rel: 'stylesheet',
                    href: url,
                }));
            });

            const linksLoaded = new Promise(resolve => {
                let nbLoaded = 0;
                $newLinks.on('load error', () => { // If we have an error, just ignore it
                    if (++nbLoaded >= $newLinks.length) {
                        resolve();
                    }
                });
            });
            $links.last().after($newLinks);
            return linksLoaded;
        });
        await Promise.all(proms).then(() => $allLinks.remove());
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
     * @param {OdooEvent} event
     * @private
     */
    _onRootEventRequest(event) {
        return this._websiteRootEvent(event.name, event.data);
    }
    _onReloadEditable(event) {
        return this.props.reloadCallback(event.data.optionSelector, event.data.url);
    }
    _onSaveRequest(event) {
        return this.save().then(() => {
            if (event.data.reload) {
                return this.props.reloadCallback(event, this.widget.el);
            }
            if (!event.data.onSuccess) {
                // If there isn't anything else to handle after the save request,
                // assume we want to exit the editor.
                return this.props.quitCallback();
            }
        });
    }
    _onContextGet(event) {
        return this._context;
    }
    _onCancelRequest(event) {
        return this.props.quitCallback();
    }
    _onSnippetDropped(event) {
        this._websiteRootEvent('widgets_start_request', event.data);
    }
    _onSnippetRemoved(event) {
        const $empty = this.$editable.find('.oe_empty');
        if (!$empty.children().length) {
            $empty.empty(); // Remove any superfluous whitespace
            this._addEditorMessages();
        }
    }
    _onMenuDialogRequest(event) {
        this.dialogs.add(MenuDialog, {
            name: event.data.name,
            url: event.data.url,
            isMegaMenu: event.data.isMegaMenu,
            save: async (...args) => {
                await event.data.save(...args);
                this.props.willReload(this.widget.el.cloneNode(true));
                this.props.reloadCallback();
            },
        });
    }
    _onPublicWidgetRequest(event) {
        // TODO: There must be a more elegant way to get
        // a public widget from the iframe.
        const Widget = this.websiteService.contentWindow.odoo.__DEBUG__.services[event.data.widgetName];
        const callback = event.data.callback;
        if (callback) {
            return callback(Widget);
        }
        return callback(Widget);
    }
    _onWillReload(event) {
        this.widget.trigger_up('disable_loading_effects')
        this.websiteService.blockIframe();
        return this.props.willReload(this.widget.el.cloneNode(true));
    }
    _onColorPreviewsUpdate(event) {
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
    _onMobilePreviewRequest() {
        this.websiteService.context.isMobile = !this.websiteService.context.isMobile;
    }
}
WysiwygAdapterComponent.prototype.events = {
    'widgets_start_request': '_onRootEventRequest',
    'widgets_stop_request': '_onRootEventRequest',
    'reload_editable': '_onReloadEditable',
    'request_save': '_onSaveRequest',
    'context_get': '_onContextGet',
    'action_demand': '_handleAction',
    'request_cancel': '_onCancelRequest',
    'snippet_dropped': '_onSnippetDropped',
    'snippet_removed': '_onSnippetRemoved',
    'reload_bundles': '_reloadBundles',
    'menu_dialog': '_onMenuDialogRequest',
    'request_public_widget': '_onPublicWidgetRequest',
    'update_color_previews': '_onColorPreviewsUpdate',
    'will_reload': '_onWillReload',
    'request_mobile_preview': '_onMobilePreviewRequest',
};
