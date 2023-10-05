/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import legacyEnv from '@web/legacy/js/common_env';

import { useService, useBus } from "@web/core/utils/hooks";
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import { requireWysiwygLegacyModule } from "@web_editor/js/frontend/loader";
import weUtils from '@web_editor/js/common/utils';
import { isMediaElement } from '@web_editor/js/editor/odoo-editor/src/utils/utils';

import { EditMenuDialog, MenuDialog } from "../dialog/edit_menu";
import { WebsiteDialog } from '../dialog/dialog';
import { PageOption } from "./page_options";
import { onWillStart, useEffect, onWillUnmount } from "@odoo/owl";

/**
 * Show/hide the dropdowns associated to the given toggles and allows to wait
 * for when it is fully shown/hidden.
 *
 * Note: this also takes care of the fact the 'toggle' method of bootstrap does
 * not properly work in all cases.
 *
 * @param {jQuery} $toggles
 * @param {boolean} [show]
 * @returns {Promise<jQuery>}
 */
function toggleDropdown($toggles, show) {
    return Promise.all($($toggles).toArray().map(toggle => {
        // We must select the element via the iframe so that the event handlers
        // declared on the iframe are triggered.
        const $toggle = toggle.ownerDocument.defaultView.$(toggle);
        const shown = toggle.classList.contains('show');
        if (shown === show) {
            return;
        }
        const toShow = !shown;
        return new Promise(resolve => {
            $toggle.parent().one(
                toShow ? 'shown.bs.dropdown' : 'hidden.bs.dropdown',
                () => resolve()
            );
            $toggle.dropdown(toShow ? 'show' : 'hide');
        });
    })).then(() => $toggles);
}

/**
 * This component adapts the Wysiwyg widget from @web_editor/wysiwyg.js.
 * It encapsulate it so that this legacy widget can work in an OWL framework.
 */
export class WysiwygAdapterComponent extends Wysiwyg {
    static props = {
        ...Wysiwyg.props,
        snippetSelector: { type: String, optional: true },
        willReload: { type: Function },
        reloadCallback: { type: Function },
        quitCallback: { type: Function },
        wysiwygReady: { type: Function },
        editableElements: { type: true, optional: true },
        savableSelector: { type: String, optional: true },
        beforeEditorActive: { type: Boolean, optional: true },
        removeWelcomeMessage: { type: Function },
    }
    /**
     * @override
     */
    setup() {
        super.setup();
        this.options = this.props.options || {};

        this.websiteService = useService('website');
        this.userService = useService('user');
        this.rpc = useService('rpc');
        this.orm = useService('orm');
        this.dialogs = useService('dialog');
        this.action = useService('action');

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
            weUtils.setEditableWindow(this.websiteService.contentWindow);
            this.switchableRelatedViews = Promise.resolve(switchableRelatedViews);
        });

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
                weUtils.setEditableWindow(window);
            }
        });
    }
    /**
     * @override
     */
    async startEdition() {
        this.props.removeWelcomeMessage();

        this.options.toolbarHandler = $('#web_editor-top-edit');
        // Do not insert a paragraph after each column added by the column commands:
        this.options.insertParagraphAfterColumns = false;

        const $editableWindow = this.$editable[0].ownerDocument.defaultView;
        // Dropdown menu initialization: handle dropdown openings by hand
        var $dropdownMenuToggles = $editableWindow.$('.o_mega_menu_toggle, #top_menu_container .dropdown-toggle');
        $dropdownMenuToggles.removeAttr('data-bs-toggle').dropdown('dispose');
        $dropdownMenuToggles.on('click.wysiwyg_megamenu', ev => {
            this.odooEditor.observerUnactive();
            var $toggle = $(ev.currentTarget);

            // Each time we toggle a dropdown, we will destroy the dropdown
            // behavior afterwards to keep manual control of it
            var dispose = ($els => $els.dropdown('dispose'));

            // First hide all other dropdown menus
            toggleDropdown($dropdownMenuToggles.not($toggle), false).then(dispose);

            // Then toggle the clicked one
            toggleDropdown($toggle)
                .then(dispose)
                .then(() => {
                    if (!this.options.enableTranslation) {
                        this._toggleMegaMenu($toggle[0]);
                    }
                })
                .then(() => this.odooEditor.observerActive());
        });

        // Ensure :blank oe_structure elements are in fact empty as ':blank'
        // does not really work with all browsers.
        for (const el of this.options.document.querySelectorAll('.oe_structure')) {
            if (!el.innerHTML.trim()) {
                $(el).empty();
            }
        }
        await super.startEdition();

        // Disable OdooEditor observer's while setting up classes
        this.odooEditor.observerUnactive();
        this._addEditorMessages();
        if (this.props.beforeEditorActive) {
            await this.props.beforeEditorActive(this.$editable);
        }
        // The jquery instance inside the iframe needs to be aware of the wysiwyg.
        this.websiteService.contentWindow.$('#wrapwrap').data('wysiwyg', this);
        await new Promise((resolve, reject) => this._websiteRootEvent('widgets_start_request', {
            editableMode: true,
            onSuccess: resolve,
            onFailure: reject,
        }));
        if (this.props.snippetSelector) {
            const $snippetEl = $(this.websiteService.pageDocument).find(this.props.snippetSelector);
            await this.snippetsMenu.activateSnippet($snippetEl);
            if ($snippetEl.length) {
                $snippetEl[0].scrollIntoView();
            }
        }
        this.props.wysiwygReady();
        // Wait for widgets to be destroyed and restarted before setting
        // the dirty observer (not to be confused with odooEditor
        // observer) as the widgets might trigger DOM mutations.
        this._setObserver();
        this.odooEditor.observerActive();
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
        return this.saveContent(false);
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
            this.el.parentElement.appendChild(this.dummyWidgetEl);
            document.body.classList.add('editor_has_dummy_snippets');
            this.props.quitCallback({ onLeave, reloadIframe });
        };

        if (!forceLeave && this._isDirty()) {
            let leaving = false;
            // The onStay/leave callbacks are not passed directly as
            // primaryClick/secondaryClick props, so that closing the dialog
            // with "esc" or the top right cross icon also executes onStay.
            this.dialogs.add(WebsiteDialog, {
                body: _t("If you discard the current edits, all unsaved changes will be lost. You can cancel to return to edit mode."),
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
    /**
     * @override
     */
    async destroy() {
        // We do not need the cache to live longer than the edition.
        // Keeping it alive could end up in a corrupt state without the user
        // even noticing. (If the values were changed in another tab or by
        // someone else, when edit starts again here, without a clear cache at
        // destroy, options will have wrong social media values).
        // It would also survive (multi) website switch, not fetching the values
        // from the accessed website.
        const mod = await requireWysiwygLegacyModule('@website/snippets/s_social_media/options');
        mod.clearDbSocialValuesCache();

        const formOptionsMod = await requireWysiwygLegacyModule('@website/snippets/s_website_form/options');
        formOptionsMod.clearAllFormsInfo();

        this._restoreMegaMenus();
        return super.destroy(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    _renderElement() {
        this.$root = this.$editable;
    }
    /**
     * @override
     * @private
     * @return {Object} Params to pass to the wysiwyg widget.
     */
    _getEditorOptions(options) {
        const powerboxItems = this._getSnippetsPowerboxItems();
        return super._getEditorOptions({
            snippets: 'website.snippets',
            recordInfo: {
                context: this._context,
                data_res_model: 'website',
                data_res_id: this._context.website_id,
            },
            toolbarOptions: {
                ...options.toolbarOptions,
                showChecklist: false,
                showAnimateText: true,
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
            ...options,
        });
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
            records = this.odooEditor.filterMutationRecords(records);
            // Skip the step for this stack because if the editor undo the first
            // step that has a dirty element, the following code would have
            // generated a new stack and break the "redo" of the editor.
            this.odooEditor.automaticStepSkipStack();
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

        this.odooEditor.addEventListener('observerUnactive', () => {
            if (this.observer) {
                processRecords(this.observer.takeRecords());
                this.observer.disconnect();
            }
        });
        this.odooEditor.addEventListener('observerActive', this._observe.bind(this));
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
     * Adds automatic editor messages on drag&drop zone elements and
     * placeholders on HTML fields.
     *
     * @private
     */
    _addEditorMessages() {
        const $wrap = this.$editable
            .find('.oe_structure.oe_empty, [data-oe-type="html"]')
            .filter(':o_editable');
        this.$editorMessageElement = $wrap.not('[data-editor-message]')
                .attr('data-editor-message-default', true)
                .attr('data-editor-message', _t('DRAG BUILDING BLOCKS HERE'));
        $wrap.filter(':empty').attr('contenteditable', false);
        for (let htmlEl of $wrap.not("[placeholder]").filter('[data-oe-sanitize="no_block"]')) {
            const placeholderText = _t("Type in text here...");
            // Put the placeholder in the same location as the powerbox hint.
            htmlEl = htmlEl.querySelector("p, div") || htmlEl;
            htmlEl.setAttribute("placeHolder", placeholderText);
            htmlEl.dataset.oeEditPlaceholder = placeholderText;
            if (htmlEl.innerText.trim().length === 0) {
                // "oe-hint" forces the display of the placeholder.
                // It is removed by OdooEditor when text is entered.
                htmlEl.classList.add("oe-hint");
            }
        }
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

        // TODO migrate in master. This stable fix restores the possibility to
        // edit the company team snippet images on subsequent editions. Indeed
        // this badly relied on the contenteditable="true" attribute being on
        // those images but it is rightfully lost after the first save. Later,
        // the o_editable_media class system was implemented and the class was
        // added in the snippet template but this did not solve existing
        // snippets in user databases.
        let $extraEditableZones = $editableSavableZones.find('.s_company_team .o_not_editable *')
            .filter((i, el) => isMediaElement(el) || el.tagName === 'IMG');
        // Same as above for social media icons.
        $extraEditableZones = $extraEditableZones.add($editableSavableZones
            .find('.s_social_media a > i'));

        // TODO find a similar system for texts.
        // grep: SOCIAL_MEDIA_TITLE_CONTENTEDITABLE
        $extraEditableZones = $extraEditableZones.add($editableSavableZones
            .find('.s_social_media .s_social_media_title'));

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
    _getUnremovableElements() {
        return [];
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
                        const snippetsMenu = this.snippetsMenu;
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
        Object.entries(bundles).forEach(([bundleName, bundleURLs]) => {
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

        // Update the panel so that color previews reflect the ones used by the
        // edited content.
        this.setCSSVariables(this.snippetsMenu.el);

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
            const range = this.getDeepRange();
            const block = this.closestElement(range.endContainer, 'p, div, ol, ul, cl, h1, h2, h3, h4, h5, h6');
            if (block) {
                block.after($clonedBody[0]);
                this.snippetsMenu.callPostSnippetDrop($clonedBody);
            }
        };
        const commands = [
            {
                category: _t('Website'),
                name: _t('Alert'),
                priority: 100,
                description: _t('Insert an alert snippet'),
                fontawesome: 'fa-info',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_alert"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Rating'),
                priority: 90,
                description: _t('Insert a rating snippet'),
                fontawesome: 'fa-star-half-o',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_rating"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Card'),
                priority: 80,
                description: _t('Insert a card snippet'),
                fontawesome: 'fa-sticky-note',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_card"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Share'),
                priority: 70,
                description: _t('Insert a share snippet'),
                fontawesome: 'fa-share-square-o',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_share"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Text Highlight'),
                priority: 60,
                description: _t('Insert a text Highlight snippet'),
                fontawesome: 'fa-sticky-note',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_text_highlight"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Chart'),
                priority: 50,
                description: _t('Insert a chart snippet'),
                fontawesome: 'fa-bar-chart',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_chart"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Progress Bar'),
                priority: 40,
                description: _t('Insert a progress bar snippet'),
                fontawesome: 'fa-spinner',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_progress_bar"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Badge'),
                priority: 30,
                description: _t('Insert a badge snippet'),
                fontawesome: 'fa-tags',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_badge"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Blockquote'),
                priority: 20,
                description: _t('Insert a blockquote snippet'),
                fontawesome: 'fa-quote-left',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
                callback: () => {
                    snippetCommandCallback('.oe_snippet_body[data-snippet="s_blockquote"]');
                },
            },
            {
                category: _t('Website'),
                name: _t('Separator'),
                priority: 10,
                description: _t('Insert an horizontal separator snippet'),
                fontawesome: 'fa-minus',
                isDisabled: () => !this.odooEditor.isSelectionInBlockRoot(),
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
        return this.isDirty() || Object.values(this.pageOptions).some(option => option.isDirty);
    }
    _trigger_up(ev) {
        const triggers = {
            'widgets_start_request': this._onRootEventRequest.bind(this),
            'widgets_stop_request': this._onRootEventRequest.bind(this),
            'ready_to_clean_for_save': this._onRootEventRequest.bind(this),
            'will_remove_snippet': this._onRootEventRequest.bind(this),
            'gmap_api_request': this._onRootEventRequest.bind(this),
            'gmap_api_key_request': this._onRootEventRequest.bind(this),
            'request_save': this._onSaveRequest.bind(this),
            'context_get': this._onContextGet.bind(this),
            'service_context_get': this._onServiceContextGet.bind(this),
            'action_demand': this._handleAction.bind(this),
            'request_cancel': this._onCancelRequest.bind(this),
            'snippet_will_be_cloned': this._onSnippetWillBeCloned.bind(this),
            'snippet_cloned': this._onSnippetCloned.bind(this),
            'snippet_dropped': this._onSnippetDropped.bind(this),
            'snippet_removed': this._onSnippetRemoved.bind(this),
            'reload_bundles': this._reloadBundles.bind(this),
            'menu_dialog': this._onMenuDialogRequest.bind(this),
            'request_mobile_preview': this._onMobilePreviewRequest.bind(this),
            'get_switchable_related_views': this._onGetSwitchableRelatedViews.bind(this),
        };


        const evType = ev.name;
        const payload = ev.data;
        if (evType in triggers) {
            triggers[evType](ev);
        } else if (evType === 'call_service') {
            const service = legacyEnv.services[payload.service];
            const result = service[payload.method].apply(service, payload.args || []);
            payload.callback(result);
        } else {
            super._trigger_up(...arguments);
        }
    }
    /**
     * @override
     * @returns {Promise}
     */
    async _saveViewBlocks() {
        await super._saveViewBlocks(...arguments);
        if (this.isDirty()) {
            return this._restoreMegaMenus();
        }
    }
    /**
     * @private
     * @param {HTMLElement} editable
     */
    _saveCoverProperties($elementToSave) {
        var el = $elementToSave.closest('.o_record_cover_container')[0];
        if (!el) {
            return;
        }

        var resModel = el.dataset.resModel;
        var resID = parseInt(el.dataset.resId);
        if (!resModel || !resID) {
            throw new Error('There should be a model and id associated to the cover');
        }

        // The cover might be dirty for another reason than cover properties
        // values only (like an editable text inside). In that case, do not
        // update the cover properties values.
        if (!('coverClass' in el.dataset)) {
            return;
        }

        this.__savedCovers = this.__savedCovers || {};
        this.__savedCovers[resModel] = this.__savedCovers[resModel] || [];

        if (this.__savedCovers[resModel].includes(resID)) {
            return;
        }
        this.__savedCovers[resModel].push(resID);

        var cssBgImage = $(el.querySelector('.o_record_cover_image')).css('background-image');
        var coverProps = {
            'background-image': cssBgImage.replace(/"/g, '').replace(window.location.protocol + "//" + window.location.host, ''),
            'background_color_class': el.dataset.bgColorClass,
            'background_color_style': el.dataset.bgColorStyle,
            'opacity': el.dataset.filterValue,
            'resize_class': el.dataset.coverClass,
            'text_align_class': el.dataset.textAlignClass,
        };

        return this.orm.write(resModel, [resID], {'cover_properties': JSON.stringify(coverProps)});
    }
    /**
     *
     * @override
     */
    async _createSnippetsMenuInstance(options = {}) {
        const snippetsEditor = await requireWysiwygLegacyModule('@website/js/editor/snippets.editor');
        const { SnippetsMenu } = snippetsEditor;
        return new SnippetsMenu(this, Object.assign({
            wysiwyg: this,
            selectorEditableArea: '.o_editable',
        }, options));
    }
    /**
     * @override
     */
    _insertSnippetMenu() {
        return this.snippetsMenu.appendTo(this.$el);
    }
    /**
     * @override
     */
    async _saveElement($el, context, withLang) {
        var promises = [];

        // Saving a view content
        await super._saveElement(...arguments);

        // Saving mega menu options
        if ($el.data('oe-field') === 'mega_menu_content') {
            // On top of saving the mega menu content like any other field
            // content, we must save the custom classes that were set on the
            // menu itself.
            // FIXME normally removing the 'show' class should not be necessary here
            // TODO check that editor classes are removed here as well
            const classes = [...$el[0].classList].filter(megaMenuClass =>
                ["dropdown-menu", "o_mega_menu", "show"].indexOf(megaMenuClass) < 0);
            promises.push(
                this.orm.write('website.menu', [parseInt($el.data('oe-id'))], {
                    'mega_menu_classes': classes.join(' '),
                })
            );
        }

        // Saving cover properties on related model if any
        var prom = this._saveCoverProperties($el);
        if (prom) {
            promises.push(prom);
        }

        return Promise.all(promises);
    }
    /**
     * Restores mega menu behaviors and closes them (important to do before
     * saving otherwise they would be saved opened).
     *
     * @private
     * @returns {Promise}
     */
    _restoreMegaMenus() {
        var $megaMenuToggles = this.$editable.find('.o_mega_menu_toggle');
        $megaMenuToggles.off('.wysiwyg_megamenu')
            .attr('data-bs-toggle', 'dropdown')
            .dropdown({});
        return toggleDropdown($megaMenuToggles, false);
    }
    /**
     * Toggles the mega menu.
     *
     * @private
     * @returns {Promise}
     */
    _toggleMegaMenu(toggleEl) {
        const megaMenuEl = toggleEl.parentElement.querySelector('.o_mega_menu');
        if (!megaMenuEl || !megaMenuEl.classList.contains('show')) {
            return this.snippetsMenu.activateSnippet(false);
        }
        megaMenuEl.classList.add('o_no_parent_editor');
        return this.snippetsMenu.activateSnippet($(megaMenuEl));
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
        const dummySnippetsEl = this.el.cloneNode(true);
        dummySnippetsEl.querySelectorAll('#oe_manipulators, .d-none, .oe_snippet_body').forEach(el => el.remove());
        dummySnippetsEl.querySelectorAll('we-input input').forEach(input => {
            input.setAttribute('value', input.closest('we-input').dataset.selectStyle || '');
        });
        return dummySnippetsEl;
    }
}
