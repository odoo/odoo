/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";

import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService, useBus } from "@web/core/utils/hooks";
import { redirect } from "@web/core/utils/urls";
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { Wysiwyg } from "@web_editor/js/wysiwyg/wysiwyg";
import weUtils from '@web_editor/js/common/utils';
import { isMediaElement } from '@web_editor/js/editor/odoo-editor/src/utils/utils';
import { cloneContentEls, checkAndNotifySEO } from "@website/js/utils";

import { EditMenuDialog, MenuDialog } from "../dialog/edit_menu";
import { WebsiteDialog } from '../dialog/dialog';
import { PageOption } from "./page_options";
import { Component, onWillStart, useEffect, onWillUnmount } from "@odoo/owl";
import { EditHeadBodyDialog } from "../edit_head_body_dialog/edit_head_body_dialog";
import { router } from "@web/core/browser/router";
import { OptimizeSEODialog } from "@website/components/dialog/seo";

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
 * Checks if the classes that changed during the mutation are all to be ignored.
 * (The mutation can be discarded if it is the case, when filtering the mutation
 * records).
 *
 * @param {Object} record the current mutation
 * @param {Array} excludedClasses the classes to ignore
 * @returns {Boolean}
 */
function checkForExcludedClasses(record, excludedClasses) {
    const classBefore = (record.oldValue && record.oldValue.split(" ")) || [];
    const classAfter = [...record.target.classList];
    const changedClasses = [
        ...classBefore.filter(c => c && !classAfter.includes(c)),
        ...classAfter.filter(c => c && !classBefore.includes(c)),
    ];
    return changedClasses.every(c => excludedClasses.includes(c));
}

/**
 * This component adapts the Wysiwyg widget from @web_editor/wysiwyg.js.
 * It extends it so that legacy widgets (options and uservalue widgets) can
 * communicate with it and with the public root.
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
        beforeEditorActive: { type: Function, optional: true },
        removeWelcomeMessage: { type: Function },
    };
    static template = "website.WysiwygAdapterComponent";
    /**
     * @override
     */
    setup() {
        super.setup();
        this.options = this.props.options || {};

        this.websiteService = useService('website');
        this.orm = useService('orm');
        this.dialogs = useService("dialog");
        this.action = useService('action');
        this.notificationService = useService("notification");

        useBus(this.websiteService.bus, 'LEAVE-EDIT-MODE', (ev) => this.leaveEditMode(ev.detail));

        this.oeStructureSelector = '#wrapwrap .oe_structure[data-oe-xpath][data-oe-id]';
        this.oeFieldSelector = '#wrapwrap [data-oe-field]:not([data-oe-sanitize-prevent-edition])';
        this.oeRecordCoverSelector = "#wrapwrap .o_record_cover_container[data-res-model]";
        this.oeCoverSelector = `#wrapwrap .s_cover[data-res-model], ${this.oeRecordCoverSelector}`;
        if (this.props.savableSelector) {
            this.savableSelector = this.props.savableSelector;
        } else {
            this.savableSelector = `${this.oeStructureSelector}, ${this.oeFieldSelector}, ${this.oeCoverSelector}`;
        }
        this.pageOptions = {};
        // Disable command palette since LinkTools take over that shortcut
        useHotkey('control+k', () => {});

        onWillStart(() => {
            // Destroy the widgets before instantiating the wysiwyg.
            // grep: RESTART_WIDGETS_EDIT_MODE
            // TODO ideally this should be done as close as the restart as
            // as possible to avoid long flickering when entering edit mode. At
            // moment some RPC are awaited before the restart so it is not
            // ideal. But this has to be done before adding o_editable classes
            // in the DOM. To review once everything is OWLified.
            this._websiteRootEvent("widgets_stop_request");

            const pageOptionEls = this.websiteService.pageDocument.querySelectorAll('.o_page_option_data');
            for (const pageOptionEl of pageOptionEls) {
                const optionName = pageOptionEl.name;
                this.pageOptions[optionName] = new PageOption(pageOptionEl, this.websiteService.pageDocument, optionName);
            }
            this.editableElements(this.$editable).addClass('o_editable');

            let switchableRelatedViews = [];
            const viewKey = this.websiteService.pageDocument.documentElement.dataset.viewXmlid;
            if (this.websiteService.isDesigner && viewKey) {
                switchableRelatedViews = rpc('/website/get_switchable_related_views', {key: viewKey});
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
            history.pushState({ skipRouteChange: true }, '');
            let hasFakeState = true;
            const leaveOnBackNavigation = () => {
                hasFakeState = false;
                this.leaveEditMode({
                    onStay: () => {
                        history.pushState({ skipRouteChange: true }, '');
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
                    // prevent router from reloading state from scratch
                    // we just want to pop the fake history entry
                    router.skipLoad = true;
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

        // Bind the _onPageClick handler to click event: to close the dropdown if clicked outside.
        this.__onPageClick = this._onPageClick.bind(this);
        this.$editable[0].addEventListener("click", this.__onPageClick, { capture: true });

        this.options.toolbarHandler = $('#web_editor-top-edit');
        // Do not insert a paragraph after each column added by the column commands:
        this.options.insertParagraphAfterColumns = false;

        const $editableWindow = this.$editable[0].ownerDocument.defaultView;
        // Dropdown menu initialization: handle dropdown openings by hand
        const $dropdownMenuToggles = $editableWindow.$(".o_mega_menu_toggle, .o_main_nav .dropdown-toggle");
        $dropdownMenuToggles.removeAttr('data-bs-toggle').dropdown('dispose');
        // Since bootstrap 5.1.3, removing bsToggle is not sufficient anymore.
        $dropdownMenuToggles.siblings(".dropdown-menu").addClass("o_wysiwyg_submenu");
        $dropdownMenuToggles.on('click.wysiwyg_megamenu', ev => {
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
                });
        });

        // Ensure :blank oe_structure elements are in fact empty as ':blank'
        // does not really work with all browsers.
        for (const el of this.options.document.querySelectorAll('.oe_structure')) {
            if (!el.innerHTML.trim()) {
                $(el).empty();
            }
        }
        await super.startEdition();

        // Overriding the `filterMutationRecords` function so it can be used to
        // filter website-specific mutations.
        const webEditorFilterMutationRecords = this.odooEditor.options.filterMutationRecords;
        Object.assign(this.odooEditor.options, {
            /**
             * @override
             */
            filterMutationRecords(records) {
                const filteredRecords = webEditorFilterMutationRecords(records);

                // Dropdown attributes to ignore.
                const dropdownClasses = ["show"];
                const dropdownToggleAttributes = ["aria-expanded"];
                const dropdownMenuAttributes = ["data-popper-placement", "style", "data-bs-popper"];
                // Offcanvas attributes to ignore.
                const offcanvasClasses = ["show"];
                const offcanvasAttributes = ["aria-modal", "aria-hidden", "role", "style"];
                // Carousel attributes to ignore.
                const carouselSlidingClasses = ["carousel-item-start", "carousel-item-end",
                    "carousel-item-next", "carousel-item-prev", "active", "o_carousel_sliding"];
                const carouselIndicatorAttributes = ["aria-current"];

                return filteredRecords.filter(record => {
                    if (record.type === "attributes") {
                        if (record.target.closest("header#top")) {
                            // Do not record when showing/hiding a dropdown.
                            if (record.target.matches(".dropdown-toggle, .dropdown-menu")
                                    && record.attributeName === "class") {
                                if (checkForExcludedClasses(record, dropdownClasses)) {
                                    return false;
                                }
                            } else if (record.target.matches(".dropdown-menu")
                                    && dropdownMenuAttributes.includes(record.attributeName)) {
                                return false;
                            } else if (record.target.matches(".dropdown-toggle")
                                    && dropdownToggleAttributes.includes(record.attributeName)) {
                                return false;
                            }

                            // Do not record when showing/hiding an offcanvas.
                            if (record.target.matches(".offcanvas, .offcanvas-backdrop")
                                    && record.attributeName === "class") {
                                if (checkForExcludedClasses(record, offcanvasClasses)) {
                                    return false;
                                }
                            } else if (record.target.matches(".offcanvas")
                                    && offcanvasAttributes.includes(record.attributeName)) {
                                return false;
                            }
                        }

                        // Do not record some carousel attributes changes.
                        if (record.target.closest(":not(section) > .carousel")) {
                            if (record.target.matches(".carousel, .carousel-item, .carousel-indicators > *")
                                    && record.attributeName === "class") {
                                if (checkForExcludedClasses(record, carouselSlidingClasses)) {
                                    return false;
                                }
                            } else if (record.target.matches(".carousel-indicators > *")
                                    && carouselIndicatorAttributes.includes(record.attributeName)) {
                                return false;
                            }
                        }
                    } else if (record.type === "childList") {
                        const addedOrRemovedNode = record.addedNodes[0] || record.removedNodes[0];
                        // Do not record the addition/removal of the offcanvas
                        // backdrop or the image snippet placeholder.
                        if (addedOrRemovedNode.nodeType === Node.ELEMENT_NODE
                                && addedOrRemovedNode.matches(".offcanvas-backdrop, .s_image")) {
                            return false;
                        }
                    }
                    return true;
                });
            }
        });

        // Disable OdooEditor observer's while setting up classes
        this.odooEditor.observerUnactive();
        this._addEditorMessages();
        if (this.props.beforeEditorActive) {
            await this.props.beforeEditorActive(this.$editable);
        }
        // The jquery instance inside the iframe needs to be aware of the wysiwyg.
        this.websiteService.contentWindow.$('#wrapwrap').data('wysiwyg', this);
        // grep: RESTART_WIDGETS_EDIT_MODE
        await new Promise((resolve, reject) => this._websiteRootEvent('widgets_start_request', {
            editableMode: true,
            onSuccess: resolve,
            onFailure: reject,
        }));
        if (this.props.snippetSelector) {
            const $snippetEl = $(this.websiteService.pageDocument).find(this.props.snippetSelector);
            await new Promise((resolve) => {
                this.snippetsMenuBus.trigger("ACTIVATE_SNIPPET", {
                    $snippet: $snippetEl,
                    onSuccess: resolve,
                });
            });
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
        // Page document might become unavailable when leaving the page.
        return this.websiteService.pageDocument?.getElementById('wrapwrap');
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
            user.context,
            {
                website_id: this.websiteService.currentWebsite.id,
                lang: this.websiteService.currentWebsite.metadata.lang,
                user_lang: user.context.lang,
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
        const mod = await odoo.loader.modules.get('@website/snippets/s_social_media/options')[Symbol.for('default')];
        mod.clearDbSocialValuesCache();

        const formOptionsMod = await odoo.loader.modules.get('@website/snippets/s_website_form/options')[Symbol.for('default')];
        formOptionsMod.clearAllFormsInfo();

        // Editable might become unavailable when leaving the page.
        this.editable?.removeEventListener("click", this.__onPageClick, { capture: true });
        return super.destroy(...arguments);
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Nothing to render for the website specialization.
     *
     * @override
     */
    _renderElement() {}
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
                showFontSize: false,
                useFontSizeInput: true,
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
            powerboxItems: powerboxItems[0],
            powerboxCategories: powerboxItems[1],
            bindLinkTool: true,
            getReadOnlyAreas: this._getReadOnlyAreas.bind(this),
            getUnremovableElements: this._getUnremovableElements.bind(this),
            direction: this.websiteService.currentWebsite.metadata.direction,
            showResponsiveFontSizesBadges: true,
            showExtendedTextStylesOptions: true,
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
                if (record.attributeName === 'contenteditable') {
                    continue;
                }

                const $savable = $(record.target).closest(this.savableSelector);
                if (!$savable.length) {
                    continue;
                }

                // Do not mark the editable dirty when simply adding/removing
                // link zwnbsp since these are just technical nodes that aren't
                // part of the user's editing of the document.
                if (record.type === 'childList' &&
                    [...record.addedNodes, ...record.removedNodes].every(node => (
                        node.nodeType === Node.TEXT_NODE && node.textContent === '\ufeff')
                    )) {
                    continue;
                }

                // Mark any savable element dirty if any tracked mutation occurs
                // inside of it.
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
                // The whole record cover is considered editable by the editor,
                // which makes it possible to add content (text, images,...)
                // from the text tools. To fix this issue, we need to reduce the
                // editable area to its editable fields only, but first, we need
                // to remove the cover along with its descendants from the
                // initial editable zones.
                return !$(el).closest('.o_not_editable').length && !el.closest(this.oeRecordCoverSelector);
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
        $extraEditableZones = $extraEditableZones.add($editableSavableZones.find('.tab-pane > .oe_structure'))
            .add(this.websiteService.pageDocument.querySelectorAll(`${this.oeRecordCoverSelector} [data-oe-field]:not([data-oe-field="arch"])`));

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
                        // TODO: Rework _onSaveRequest to not take Events
                        this._onSaveRequest({ data: { reload: true} });
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
        const bundles = await rpc('/website/theme_customize_bundle_reload');
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
            const range = this.getDeepRange();
            const block = this.closestElement(range.endContainer, 'p, div, ol, ul, cl, h1, h2, h3, h4, h5, h6');
            if (block) {
                this.snippetsMenuBus.trigger("INSERT_SNIPPET", { snippetSelector: selector, block });
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
        // TODO improve in master: the way we check if the page is dirty should
        // match the fact the save will actually do something or not. Right now,
        // this check checks the whole page, including the non editable parts,
        // regardless of the fact something can be saved inside or not. It is
        // also thus of course considering the page dirty too often by mistake
        // since non editable parts can have their DOM changed without impacting
        // the save (e.g. menus being folded into the "+" menu for example).
        return this.isDirty() || Object.values(this.pageOptions).some(option => option.isDirty);
    }
    _trigger_up(ev) {
        const triggers = {
            'widgets_start_request': this._onRootEventRequest.bind(this),
            'widgets_stop_request': this._onRootEventRequest.bind(this),
            'will_remove_snippet': this._onRootEventRequest.bind(this),
            'request_save': this._onSaveRequest.bind(this),
            'context_get': this._onContextGet.bind(this),
            'action_demand': this._handleAction.bind(this),
            'request_cancel': this._onCancelRequest.bind(this),
            'snippet_will_be_cloned': this._onSnippetWillBeCloned.bind(this),
            'snippet_cloned': this._onSnippetCloned.bind(this),
            'snippet_removed': this._onSnippetRemoved.bind(this),
            'reload_bundles': this._reloadBundles.bind(this),
            'menu_dialog': this._onMenuDialogRequest.bind(this),
            'open_edit_head_body_dialog': this._onOpenEditHeadBodyDialog.bind(this),
        };


        const evType = ev.name;
        const payload = ev.data;
        if (evType in triggers) {
            triggers[evType](ev);
        } else if (evType === 'call_service') {
            const service = Component.env.services[payload.service];
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
        this._restoreCarousels();
        await super._saveViewBlocks(...arguments);
        if (this.isDirty()) {
            return this._restoreMegaMenus();
        }
    }
    /**
     * @private
     * @param {HTMLElement} editable
     */
    async _saveCoverProperties($elementToSave) {
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

        const imageEl = el.querySelector('.o_record_cover_image');
        let cssBgImage = imageEl.style.backgroundImage;
        if (imageEl.classList.contains("o_b64_image_to_save")) {
            imageEl.classList.remove("o_b64_image_to_save");
            const groups = cssBgImage.match(/url\("data:(?<mimetype>.*);base64,(?<imageData>.*)"\)/)?.groups;
            if (!groups.imageData) {
                // Checks if the image is in base64 format for RPC call. Relying
                // only on the presence of the class "o_b64_image_to_save" is not
                // robust enough.
                return;
            }
            const modelName = await this.websiteService.getUserModelName(resModel);
            const recordNameEl = imageEl.closest("body").querySelector(`[data-oe-model="${resModel}"][data-oe-id="${resID}"][data-oe-field="name"]`);
            const recordName = recordNameEl ? `'${recordNameEl.textContent.replaceAll("/", "")}'` : resID;
            const attachment = await rpc(
                '/web_editor/attachment/add_data',
                {
                    name: `${modelName} ${recordName} cover image.${groups.mimetype.split("/")[1]}`,
                    data: groups.imageData,
                    is_image: true,
                    res_model: 'ir.ui.view',
                },
            );
            cssBgImage = `url(${attachment.image_src})`;
        }
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
     * @override
     */
    async getSnippetsMenuClass() {
        const snippetsEditor = await odoo.loader.modules.get('@website/js/editor/snippets.editor')[Symbol.for('default')];
        const { SnippetsMenu } = snippetsEditor;
        return SnippetsMenu;
    }
    /**
     * @override
     */
    async _saveElement($el, context, withLang, ...rest) {
        var promises = [];

        // Saving Embed Code snippets with <script> in the database, as these
        // elements are removed in edit mode.
        if ($el[0].querySelector(".s_embed_code")) {
            // Copied so as not to impact the actual DOM and prevent scripts
            // from loading.
            const $clonedEl = $el.clone(true, true);
            for (const embedCodeEl of $clonedEl[0].querySelectorAll(".s_embed_code")) {
                const embedTemplateEl = embedCodeEl.querySelector(".s_embed_code_saved");
                if (embedTemplateEl) {
                    embedCodeEl.querySelector(".s_embed_code_embedded")
                        .replaceChildren(cloneContentEls(embedTemplateEl.content, true));
                }
            }
            await super._saveElement($clonedEl, context, withLang, ...rest);
        } else {
            // Saving a view content
            await super._saveElement(...arguments);
        }

        // Saving mega menu options
        if ($el.data('oe-field') === 'mega_menu_content') {
            // On top of saving the mega menu content like any other field
            // content, we must save the custom classes that were set on the
            // menu itself.
            // FIXME normally removing the 'show' class should not be necessary here
            // TODO check that editor classes are removed here as well
            const classes = [...$el[0].classList].filter(megaMenuClass =>
                ["dropdown-menu", "o_mega_menu", "show", "o_wysiwyg_submenu"].indexOf(megaMenuClass) < 0);
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
            return new Promise((resolve) => this.snippetsMenuBus.trigger("ACTIVATE_SNIPPET", {
                $snippet: false,
                onSuccess: resolve,
            }));
        }
        return new Promise((resolve) => {
            return this.snippetsMenuBus.trigger("ACTIVATE_SNIPPET", { $snippet: $(megaMenuEl), onSuccess: resolve });
        });
    }
    /**
     * Restores all the carousels so their first slide is the active one.
     *
     * @private
     */
    _restoreCarousels() {
        this.$editable[0].querySelectorAll(".carousel").forEach(carouselEl => {
            // Set the first slide as the active one.
            carouselEl.querySelectorAll(".carousel-item").forEach((itemEl, i) => {
                itemEl.classList.remove("next", "prev", "left", "right");
                itemEl.classList.toggle("active", i === 0);
            });
            carouselEl.querySelectorAll(".carousel-indicators > *").forEach((indicatorEl, i) => {
                indicatorEl.classList.toggle("active", i === 0);
                indicatorEl.removeAttribute("aria-current");
                if (i === 0) {
                    indicatorEl.setAttribute("aria-current", "true");
                }
            });
        });
    }
    /**
     * @override
     */
    _getRecordInfo(editable) {
        const $editable = $(editable);
        return {
            resModel: $editable.data('oe-model'),
            resId: $editable.data('oe-id'),
            field: $editable.data('oe-field'),
            type: $editable.data('oe-type'),
        };
    }
    /**
     * Hides all opened dropdowns.
     *
     * @private
     */
    _hideDropdowns() {
        for (const toggleEl of this.$editable[0].querySelectorAll(".dropdown-toggle.show")) {
            Dropdown.getOrCreateInstance(toggleEl).hide();
        }
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
        const isDirty = this._isDirty();
        let callback = () => {
            this.leaveEditMode({ forceLeave: true });
            const canPublish = this.websiteService.currentWebsite.metadata.canPublish;
            if (
                isDirty &&
                (!canPublish ||
                    (canPublish && this.websiteService.currentWebsite.metadata.isPublished)) &&
                this.websiteService.currentWebsite.metadata.canOptimizeSeo
            ) {
                const {
                    mainObject: { id, model },
                } = this.websiteService.currentWebsite.metadata;
                rpc("/website/get_seo_data", {
                    res_id: id,
                    res_model: model,
                }).then(
                    (seo_data) =>
                        checkAndNotifySEO(seo_data, OptimizeSEODialog, {
                            notification: this.notificationService,
                            dialog: this.dialogs,
                        }),
                    (error) => {
                        throw error;
                    }
                );
            }
        };
        if (event.data.reload || event.data.reloadEditor) {
            this.props.willReload(this._getDummmySnippetsEl());
            callback = async () => {
                if (event.data.onSuccess) {
                    await event.data.onSuccess();
                }
                return this.props.reloadCallback({
                    snippetOptionSelector: event.data.optionSelector,
                    url: event.data.url,
                });
            };
        } else if (event.data.onSuccess) {
            callback = event.data.onSuccess;
        } else if (event.data.reloadWebClient) {
            const currentPath = encodeURIComponent(window.location.pathname);
            const websiteId = this.websiteService.currentWebsite.id;
            callback = () => redirect(`/odoo/action-website.website_preview?website_id=${encodeURIComponent(websiteId)}&path=${currentPath}&enable_editor=1`);
        } else if (event.data.action) {
            callback = () => {
                this.leaveEditMode({
                    onLeave: () => this.action.doAction(event.data.action, event.data.options || {}),
                    forceLeave: true,
                    reloadIframe: false,
                });
            };
        }
        if (this._isDirty() || this.options.enableTranslation) {
            return this.save().then(callback, event.data.onFailure);
        } else {
            return callback();
        }
    }
    /**
     * Returns the user context.
     * @link {@web/core/user.js}
     *
     * @param event
     * @returns {*}
     * @private
     */
    _onContextGet(event) {
        return event.data.callback(this._context);
    }
    /**
     * @param {OdooEvent}
     * @private
     */
    _onOpenEditHeadBodyDialog(ev) {
        this.dialogs.add(EditHeadBodyDialog, {}, {
            onClose: ev.data.onSuccess,
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
    _onSnippetDropped({ $target, addPostDropAsync }) {
        addPostDropAsync(new Promise(resolve => {
            this._websiteRootEvent('widgets_start_request', {
                editableMode: true,
                $target,
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
     * Called when a child needs to know about the views that can
     * be toggled on or off on a specific view related to the editable.
     *
     * @param event
     * @returns {Promise<void>}
     * @private
     */
    _getSwitchableRelatedViews(event) {
        return this.switchableRelatedViews;
    }
    /**
     * This method returns a visual skeleton of the snippets menu, by making a
     * copy of the Wysiwyg element. This is used when reloading the iframe or
     * leaving the edit mode, so that the widget can be destroyed under the
     * hood (ideally, the Wysiwyg would remove its listeners on the document,
     * so that they are not triggered during a reload).
     */
    _getDummmySnippetsEl() {
        const dummySnippetsEl = this.snippetsMenuContainer.el.cloneNode(true);
        dummySnippetsEl.querySelectorAll('#oe_manipulators, .d-none, .oe_snippet_body').forEach(el => el.remove());
        dummySnippetsEl.querySelectorAll('we-input input').forEach(input => {
            input.setAttribute('value', input.closest('we-input').dataset.selectStyle || '');
        });
        return dummySnippetsEl;
    }
    /**
     * Stop public widgets within the iframe.
     */
    _widgetsStopRequest() {
        this._websiteRootEvent('widgets_stop_request');
    }
    /**
     * Called when the page is clicked anywhere.
     * Closes the shown dropdown if the click is outside of it.
     *
     * @private
     * @param {Event} ev
     */
    _onPageClick(ev) {
        if (ev.target.closest(".dropdown-menu.show, .dropdown-toggle.show")) {
            return;
        }
        this._hideDropdowns();
    }
}
