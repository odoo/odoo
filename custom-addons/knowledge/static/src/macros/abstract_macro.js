/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { isVisible } from "@web/core/utils/ui";
import { MacroEngine } from "@web/core/macro";

class KnowledgeMacroError extends Error {}

/**
 * Abstract class for Knowledge macros, that will be used to interact like a
 * tour with a Form view chatter and/or html field.
 */
export class AbstractMacro {
    /**
     * @param {Object} options
     * @param {HTMLElement} options.targetXmlDoc
     * @param {Array[Object]} options.breadcrumbs
     * @param {Any} options.data
     * @param {Object} options.services required: action, dialog, ui
     */
    constructor ({
        targetXmlDoc,
        breadcrumbs,
        data,
        services
    }) {
        this.targetXmlDoc = targetXmlDoc;
        this.targetBreadcrumbs = breadcrumbs;
        this.data = data;
        this.engine = new MacroEngine({ defaultCheckDelay: 16 });
        this.services = services;
        this.blockUI = { action: function () {
            if (!this.services.ui.isBlocked) {
                this.services.ui.block();
            }
        }.bind(this) };
        this.unblockUI = { action: function () {
            if (this.services.ui.isBlocked) {
                this.services.ui.unblock();
            }
        }.bind(this) };
        this.onError = this.onError.bind(this);
    }
    start() {
        // Build the desired macro action
        const macroAction = this.macroAction();
        if (!macroAction || !macroAction.steps || !macroAction.steps.length) {
            return;
        }
        /**
         * Preliminary breadcrumbs macro. It will use the @see breadcrumbsIndex
         * to switch back to the view related to the stored record
         * (@see KnowledgeCommandsService ). Once and if the view of the target
         * record is correctly loaded, run the specific macroAction.
         */
        const startMacro = {
            name: "restore_record",
            onError: this.onError,
            steps: [
                this.blockUI, {
                // Restore the target Form view through its breadcrumb jsId.
                trigger: () => {
                    // Ensure that we have a breadcrumb sequence displayed for
                    // the user. Any breadcrumb element will do as a witness
                    // since the Form view won't be restored through the
                    // breadcrumbs, but with the controller.
                    const breadcrumbEl = document.querySelector(`.breadcrumb-item:not(.active)`);
                    if (!breadcrumbEl) {
                        return null;
                    }
                    return breadcrumbEl;
                },
                action: async () => {
                    try {
                        // Try to restore the target controller.
                        await this.services.action.restore(this.targetBreadcrumbs.at(-1).jsId);
                    } catch {
                        // If the controller is unreachable, abort the macro.
                        throw new KnowledgeMacroError(
                            _t('The record that this macro is targeting could not be found.')
                        );
                    }
                },
            }, {
                // Start the requested macro when the current breadcrumbs
                // match the target Form view.
                trigger: () => {
                    const controllerBreadcrumbs = this.services.action.currentController.config.breadcrumbs;
                    if (this.targetBreadcrumbs.at(-1).jsId === controllerBreadcrumbs.at(-1)?.jsId) {
                        return this.getFirstVisibleElement.bind(this, '.o_breadcrumb .o_last_breadcrumb_item');
                    }
                    return null;
                },
                action: this.engine.activate.bind(this.engine, macroAction),
            }],
        };
        this.engine.activate(startMacro);
    }
    /**
     * @param {Error} error
     * @param {Object} step
     * @param {integer} index
     */
    onError(error, step, index) {
        this.unblockUI.action();
        if (error instanceof KnowledgeMacroError) {
            this.services.dialog.add(AlertDialog,{
                body: error.message,
                title: _t('Error'),
                confirmLabel: _t('Close'),
            });
        } else {
            console.error(error);
        }
    }
    /**
     * Searches for the first element in the dom matching the selector. The
     * results are filtered with `filter` and the returned element is either
     * the first or the last depending on `reverse`.
     *
     * @param {String|HTMLElement} selector
     * @param {Function} filter
     * @param {boolean} reverse
     * @returns {HTMLElement}
     */
    getFirstVisibleElement(selector, filter=false, reverse=false) {
        const elementsArray = typeof(selector) === 'string' ? Array.from(document.querySelectorAll(selector)) : [selector];
        const sel = filter ? elementsArray.filter(filter) : elementsArray;
        for (let i = 0; i < sel.length; i++) {
            i = reverse ? sel.length - 1 - i : i;
            if (isVisible(sel[i])) {
                return sel[i];
            }
        }
        return null;
    }
    /**
     * Validate that the macro is still on the correct Form view by checking
     * that the target breadcrumbs are the same as the current ones. To be used
     * at each step inside the target Form view. Throwing an error will
     * terminate the macro.
     */
    validatePage() {
        const controllerBreadcrumbs = this.services.action.currentController.config.breadcrumbs;
        if (this.targetBreadcrumbs.at(-1).jsId !== controllerBreadcrumbs.at(-1)?.jsId) {
            throw new KnowledgeMacroError(
                _t('The record that this macro is targeting could not be found.')
            );
        }
    }
    /**
     * To be overridden by an actual Macro implementation. It should contain
     * the steps to be executed on the target Form view.
     *
     * @returns {Object}
     */
    macroAction() {
        return {
            name: this.constructor.name,
            onError: this.onError,
            steps: [],
            timeout: 10000,
            onTimeout: () => {
                throw new KnowledgeMacroError(
                    _t('The operation could not be completed.')
                );
            }
        };
    }
    /**
     * Handle the case where an item is hidden in a tab of the form view
     * notebook. Only pages with the "name" attribute set can be navigated to.
     * Other pages are ignored (and the fields they contain are too).
     * @see FormControllerPatch
     *
     * @param {String} targetSelector selector (will be used in the target
     * xml document) for the element (likely an html field) that could be
     * hidden inside a non-active tab of the notebook.
     */
    searchInXmlDocNotebookTab(targetSelector) {
        const searchElement = this.targetXmlDoc.querySelector(targetSelector);
        const page = searchElement ? searchElement.closest('page') : undefined;
        const pageName = page ? page.getAttribute('name') : undefined;
        if (!pageName) {
            return;
        }
        const pageEl = this.getFirstVisibleElement(`.o_notebook .nav-link[name=${pageName}]:not(.active)`);
        if (pageEl) {
            pageEl.click();
        }
    }
}
