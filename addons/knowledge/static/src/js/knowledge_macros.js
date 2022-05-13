/** @odoo-module */

import { MacroEngine } from "@web/core/macro";
import Dialog from "web.Dialog";
import core from "web.core";
const _t = core._t;

/**
 * Wrapper for @see Macro destined to be used by @see KnowledgeToolbar buttons.
 * These macros will navigate through breadcrumbs to inject information from
 * a Knowledge article into a previously browsed record that met the
 * requirements specified in @see FormController (Knowledge)
 */
class KnowledgeMacroPageChangeError extends Error {}
export class KnowledgeMacro {
    /**
     * @param {Object} breadcrumbs
     * @param {string} action name of the action to be undertaken
     * @param {Object} data data object to be used during the action
     * @param {Object} uiService used to cover the screen during the macro
     * @param {integer} interval delay between the macro steps
     */
    constructor (breadcrumbs, action, data, uiService, interval = 16) {
        this.breadcrumbsIndex = breadcrumbs.length - 1;
        this.breadcrumbsTitle = breadcrumbs[this.breadcrumbsIndex].title;
        this.breadcrumbsSelector = `[role="navigation"] > .breadcrumb-item:contains(${this.breadcrumbsTitle})`;
        this.interval = interval;
        this.data = data;
        this.engine = new MacroEngine();
        this.action = action;
        this.uiService = uiService;
        this.blockUI = { action: function () {
            if (!this.uiService.isBlocked) {
                this.uiService.block();
            }
        }.bind(this) };
        this.unblockUI = { action: function () {
            if (this.uiService.isBlocked) {
                this.uiService.unblock();
            }
        }.bind(this) };
    }
    /**
     * Execute the specified macro
     */
    start() {
        // Build the desired macro action
        const macroAction = this._macroActions(this.action);
        if (!macroAction) {
            return;
        }
        /**
         * Preliminary breadcrumbs macro. It will use the @see breadcrumbsIndex
         * to switch back to the view related to the stored record
         * (@see KnowledgeService) . Once and if the view of the target record
         * is correctly loaded, run the specific macroAction.
         */
        const startMacro = {
            name: "restore_record",
            interval: this.interval,
            onError: this.onError.bind(this),
            steps: [
                this.blockUI, {
                trigger: function () {
                    const $breadcrumbs = $(`.breadcrumb-item:not(.active)`);
                    if ($breadcrumbs.length > this.breadcrumbsIndex) {
                        const breadcrumb = $breadcrumbs[this.breadcrumbsIndex];
                        if (breadcrumb.textContent.includes(this.breadcrumbsTitle)) {
                            return this.getElement(breadcrumb.querySelector('a'));
                        }
                    }
                    return null;
                }.bind(this),
                action: 'click',
            }, {
                trigger: this.getElement.bind(this, `${this.breadcrumbsSelector}.active`),
                action: this.engine.activate.bind(this.engine, macroAction),
            }],
        };
        this.engine.activate(startMacro);
    }
    /**
     * @see Macro
     *
     * @param {Error} error
     * @param {Object} step
     * @param {integer} index
     */
    onError(error, step, index) {
        this.unblockUI.action();
        if (error instanceof KnowledgeMacroPageChangeError) {
            Dialog.alert(this,
                _t('The operation was interrupted because the page or the record changed. Please try again later.'), {
                title: _t('Error'),
            });
        } else {
            console.error(error);
        }
    }
    /**
     * Return the first (or the last) matching element from selector only if it
     * is currently visible for the user in the document.
     *
     * @param {string} selector
     * @param {boolean} reverse whether to search from the end to the start
     * @returns {Element}
     */
    getElement(selector, reverse=false) {
        const $sel = $(selector);
        for (let i = 0; i < $sel.length; i++) {
            i = reverse ? $sel.length - 1 - i : i;
            if ($sel.eq(i).is(':visible:hasVisibility')) {
                return $sel[i];
            }
        }
        return null;
    }
    /**
     * Validate the page during the macro action. The page is valid if the
     * targeted breadcrumb is currently active. Abort a macro in case of failure
     * @see Macro
     */
    validatePage() {
        if (!this.getElement(`${this.breadcrumbsSelector}.active`)) {
            throw new KnowledgeMacroPageChangeError();
        }
    }
    /**
     * Build the desired action description from this.properties. Every macro
     * will validate the page at every step and abort upon failure to do so.
     *
     * @param {string} action name of a handled macro action
     * @returns {Object} valid descrption @see Macro
     */
    _macroActions(action) {
        switch (action) {
            /**
             * @see TemplateToolbar
             * Copy the contents of a /template block and paste into the
             * targeted field stored in @see data . This macro is able to switch
             * form notebook panes if the field is available in one of them.
             */
            case "use_as_description": return {
                name: action,
                interval: this.interval,
                onError: this.onError.bind(this),
                steps: [{
                    trigger: function () {
                        this.validatePage();
                        const selector = `.oe_form_field_html[name="${this.data.fieldName}"]`;
                        const el = this.getElement(selector);
                        if (el) {
                            return el;
                        }
                        // Handle the case where the field is hidden in a tab of the form view notebook
                        const $sel = $(selector);
                        for (let i = 0; i < $sel.length; i++) {
                            const pane = $sel[i].closest('.tab-pane:not(.active)');
                            if (pane) {
                                const paneSwitch = this.getElement(`[data-toggle="tab"][href*="${pane.id}"]`);
                                if (paneSwitch) {
                                    paneSwitch.click();
                                    break;
                                }
                            }
                        }
                        return null;
                    }.bind(this),
                    action: 'click',
                }, {
                    trigger: function () {
                        this.validatePage();
                        return this.getElement(`.oe_form_field_html[name="${this.data.fieldName}"] > .odoo-editor-editable`);
                    }.bind(this),
                    action: this._pasteTemplate.bind(this),
                }, this.unblockUI],
            };
            /**
             * @see TemplateToolbar
             * Copy the contents of a /template block and paste into a new
             * chatter message in the targeted record context. Open the full
             * composer to access the editor.
             */
            case "send_as_message": return {
                name: action,
                interval: this.interval,
                onError: this.onError.bind(this),
                steps: [{
                    trigger: function() {
                        this.validatePage();
                        return this.getElement('.o_ChatterTopbar_buttonSendMessage');
                    }.bind(this),
                    action: (el) => {
                        if (!el.classList.contains('o-active')) {
                            el.click();
                        }
                    },
                }, {
                    trigger: function() {
                        this.validatePage();
                        return this.getElement('.o_Composer_buttonFullComposer');
                    }.bind(this),
                    action: 'click',
                }, {
                    trigger: function () {
                        this.validatePage();
                        const dialog = this.getElement('.o_dialog_container.modal-open');
                        if (dialog) {
                            return this.getElement(dialog.querySelector('.oe_form_field_html[name="body"] > .odoo-editor-editable'));
                        } else {
                            return null;
                        }
                    }.bind(this),
                    action: this._pasteTemplate.bind(this),
                }, this.unblockUI],
            };
            /**
             * @see FileToolbar
             * Attach a file to a new chatter message in the targeted record
             * context.
             */
            case "attach_to_message": return {
                name: action,
                interval: this.interval,
                onError: this.onError.bind(this),
                steps: [{
                    trigger: function() {
                        this.validatePage();
                        return this.getElement('.o_ChatterTopbar_buttonSendMessage');
                    }.bind(this),
                    action: (el) => {
                        el.scrollIntoView();
                        if (!el.classList.contains('o-active')) {
                            el.click();
                        }
                    },
                }, {
                    trigger: function() {
                        this.validatePage();
                        return this.getElement('.o_Composer_buttonAttachment');
                    }.bind(this),
                    action: this._dragAndDrop.bind(this, 'dragenter'),
                }, {
                    trigger: function () {
                        this.validatePage();
                        return this.getElement('.o_Composer_dropZone');
                    }.bind(this),
                    action: this._dragAndDrop.bind(this, 'drop'),
                }, this.unblockUI],
            };
            /**
             * @see FileToolbar
             * Attach a file to the targeted record.
             */
            case "use_as_attachment": return {
                name: action,
                interval: this.interval,
                onError: this.onError.bind(this),
                steps: [{
                    trigger: function() {
                        this.validatePage();
                        return this.getElement('.o_ChatterTopbar_buttonAttachments');
                    }.bind(this),
                    action: function(el) {
                        if (!this.getElement('.o_AttachmentBox_content')) {
                            el.click();
                        }
                    }.bind(this),
                }, {
                    trigger: function() {
                        this.validatePage();
                        return this.getElement('.o_AttachmentBox_content');
                    }.bind(this),
                    action: (el) => el.scrollIntoView(),
                }, this.unblockUI],
            };
        }
    }
    /**
     * Handle drag&drop events with the dataTransfer object stored in @see data
     *
     * @param {string} type event type (related to drag&drop)
     * @param {Element} el target element
     */
    _dragAndDrop(type, el) {
        const fakeDragAndDrop = new Event(type, {
            bubbles: true,
            cancelable: true,
            composed: true,
        });
        fakeDragAndDrop.dataTransfer = this.data.dataTransfer;
        el.dispatchEvent(fakeDragAndDrop);
    }
    /**
     * Handle paste event with the dataTransfer object stored in @see data
     *
     * @param {Element} el target element
     */
    _pasteTemplate(el) {
        const fakePaste = new Event('paste', {
            bubbles: true,
            cancelable: true,
            composed: true,
        });
        fakePaste.clipboardData = this.data.dataTransfer;

        const sel = document.getSelection();
        sel.removeAllRanges();
        const range = document.createRange();
        const firstChild = el.firstChild;
        if (!firstChild) {
            range.setStart(el, 0);
            range.setEnd(el, 0);
        } else {
            range.setStartBefore(firstChild);
            range.setEndBefore(firstChild);
        }
        sel.addRange(range);
        el.dispatchEvent(fakePaste);
    }
}
