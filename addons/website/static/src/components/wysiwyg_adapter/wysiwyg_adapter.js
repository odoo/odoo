/** @odoo-module */

import { ComponentAdapter } from 'web.OwlCompatibility';

import { useWowlService } from '@web/legacy/utils';


const { onWillStart, useEffect } = owl;

/**
 * This component adapts the Wysiwyg widget from @web_editor/wysiwyg.js.
 * In reality it encapsulate it so that this legacy widget can work in an OWL
 * framework.
 */
export class WysiwygAdapterComponent extends ComponentAdapter {
    /**
     * @override
     */
    setup() {
        super.setup();
        const options = this.props.options || {};

        this.websiteService = useWowlService('website');
        this.oeStructureSelector = '#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]';
        this.oeFieldSelector = '#wrapwrap [data-oe-field]';
        this.oeCoverSelector = '#wrapwrap .s_cover[data-res-model], #wrapwrap .o_record_cover_container[data-res-model]';
        if (options.savableSelector) {
            this.savableSelector = options.savableSelector;
        } else {
            this.savableSelector = `${this.oeStructureSelector}, ${this.oeFieldSelector}, ${this.oeCoverSelector}`;
        }
        useEffect(() => {
            const initWysiwyg = async () => {
                this.$editable.on('click.odoo-website-editor', '*', this, this._preventDefault);
                // Disable OdooEditor observer's while setting up classes
                this.widget.odooEditor.observerUnactive();
                this._addEditorMessages();
                this.widget.odooEditor.observerActive();
                this._setObserver();

                if (this.props.snippetSelector) {
                    const snippetEl = $(this.websiteService.pageDocument).find(this.props.snippetSelector);
                    await this.widget.snippetsMenu.activateSnippet($(snippetEl));
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

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @return {Object} Params to pass to the wysiwyg widget.
     */
    get _wysiwygParams() {
        const context = this.userService.context;
        return {
            snippets: 'website.snippets',
            recordInfo: {
                context: context,
                data_res_model: 'website',
                data_res_id: context.website_id,
            },
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
            showEmptyElementHint: false,
            getReadOnlyAreas: this._getReadOnlyAreas.bind(this),
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
        return {};
    }
}
