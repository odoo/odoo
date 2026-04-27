/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { isVisible } from "@web/core/utils/ui";
import { Macro } from "@web/core/macro";

class KnowledgeMacroError extends Error {}

/**
 * Abstract class for Knowledge macros, that will be used to interact like a
 * tour with a Form view chatter and/or html field.
 */
export class AbstractMacro extends Macro {
    /**
     * @param {Object} options
     * @param {HTMLElement} options.targetXmlDoc
     * @param {Array[Object]} options.breadcrumbs
     * @param {Any} options.data
     * @param {Object} options.services required: action, dialog, ui
     */
    constructor({ targetXmlDoc, breadcrumbs, data, services }) {
        super({
            name: "restore_recort",
            steps: [],
        });
        this.targetXmlDoc = targetXmlDoc;
        this.targetBreadcrumbs = breadcrumbs;
        this.data = data;
        this.services = services;
        this.steps = this.buildSteps();
    }

    blockUI() {
        if (!this.services.ui.isBlocked) {
            this.services.ui.block();
        }
    }

    buildSteps() {
        // Build the desired macro action
        const steps = this.getSteps();
        if (!steps.length) {
            return [];
        }
        /**
         * Preliminary breadcrumbs macro. It will use the @see breadcrumbsIndex
         * to switch back to the view related to the stored record
         * (@see KnowledgeCommandsService ). Once and if the view of the target
         * record is correctly loaded, run the specific macroAction.
         */
        return [
            {
                action: () => this.blockUI(),
            },
            {
                // Restore the target Form view through its breadcrumb jsId.
                trigger: () => {
                    return document.querySelector(`.o_knowledge_header i.oi-chevron-left`);
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
            },
            {
                // Start the requested macro when the current breadcrumbs
                // match the target Form view.
                trigger: () => {
                    const controllerBreadcrumbs = this.services.action.currentController.config.breadcrumbs;
                    if (this.targetBreadcrumbs.at(-1).jsId === controllerBreadcrumbs.at(-1)?.jsId) {
                        return this.getFirstVisibleElement(".o_breadcrumb .o_last_breadcrumb_item");
                    }
                    return null;
                },
            },
            ...steps,
        ];
    }

    /**
     * @param {Error} error
     * @param {Object} step
     * @param {integer} index
     */
    onError(error, step, index) {
        this.blockUI();
        if (error instanceof KnowledgeMacroError) {
            this.services.dialog.add(AlertDialog, {
                body: error.message,
                title: _t("Error"),
                confirmLabel: _t("Close"),
            });
        } else {
            console.error(error);
        }
    }

    onTimeout() {
        throw new KnowledgeMacroError(_t("The operation could not be completed."));
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
     * To be overridden by an actual Macro implementation. It should contain
     * the steps to be executed on the target Form view.
     *
     * @returns {Array[Object]}
     */
    getSteps() {
        return [];
    }

    unblockUI() {
        if (this.services.ui.isBlocked) {
            this.services.ui.unblock();
        }
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
