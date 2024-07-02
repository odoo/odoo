/** @odoo-module **/
import * as hoot from "@odoo/hoot-dom";
import { markup } from "@odoo/owl";
import { isMacOS } from "@web/core/browser/feature_detection";
import { _t } from "@web/core/l10n/translation";
import { utils } from "@web/core/ui/ui_service";

/**
 * @typedef {string | (actions: RunningTourActionHelper) => void | Promise<void>} RunCommand
 *
 * @typedef ConsumeEvent
 * @property {string} name
 * @property {Element} target
 * @property {(ev: Event) => boolean} conditional
 */

/**
 * Calls the given `func` then returns/resolves to `true`
 * if it will result to unloading of the page.
 * @param {(...args: any[]) => void} func
 * @param  {any[]} args
 * @returns {boolean | Promise<boolean>}
 */
export function callWithUnloadCheck(func, ...args) {
    let willUnload = false;
    const beforeunload = () => (willUnload = true);
    window.addEventListener("beforeunload", beforeunload);
    const result = func(...args);
    if (result instanceof Promise) {
        return result.then(() => {
            window.removeEventListener("beforeunload", beforeunload);
            return willUnload;
        });
    } else {
        window.removeEventListener("beforeunload", beforeunload);
        return willUnload;
    }
}

/**
 *
 * @param {TourStep} step
 * @returns {{
 *  event: string,
 *  anchor: string,
 *  altAnchor: string | undefined,
 * }[]}
 */
export function getSubActions(step) {
    const actions = [];
    if (!step.run || typeof step.run === "function") {
        return [];
    }

    for (const todo of step.run.split("&&")) {
        const m = String(todo)
            .trim()
            .match(/^(?<action>\w*) *\(? *(?<arguments>.*?)\)?$/);

        const a = m.groups?.action;
        const anchor = m.groups?.arguments || step.trigger;
        if (a === "drag_and_drop") {
            actions.push({
                event: "drag",
                anchor: step.trigger,
            });
            actions.push({
                event: "drop",
                anchor,
            });
        } else {
            actions.push({
                event: a,
                anchor: a === "edit" ? step.trigger : anchor,
                altAnchor: step.alt_trigger,
            });
        }
    }

    return actions;
}

/**
 * @param {HTMLElement} [element]
 * @param {RunCommand} [runCommand]
 * @returns {ConsumeEvent[]}
 */
export function getConsumeEventType(element, runCommand) {
    const consumeEvents = [];
    if (runCommand === "click") {
        consumeEvents.push({
            name: "click",
            target: element,
        });

        // Use the hotkey should also consume
        if (element.hasAttribute("data-hotkey")) {
            consumeEvents.push({
                name: "keydown",
                target: element,
                conditional: (ev) =>
                    ev.key === element.getAttribute("data-hotkey") &&
                    (isMacOS() ? ev.ctrlKey : ev.altKey),
            });
        }

        // Click on a field widget with an autocomplete should be also completed with a selection though Enter or Tab
        // This case is for the steps that click on field_widget
        if (element.querySelector(".o-autocomplete--input")) {
            consumeEvents.push({
                name: "keydown",
                target: element.querySelector(".o-autocomplete--input"),
                conditional: (ev) =>
                    ["Tab", "Enter"].includes(ev.key) &&
                    ev.target.parentElement.querySelector(
                        ".o-autocomplete--dropdown-item .ui-state-active"
                    ),
            });
        }

        // Click on an element of a dropdown should be also completed with a selection though Enter or Tab
        // This case is for the steps that click on a dropdown-item
        if (element.closest(".o-autocomplete--dropdown-menu")) {
            consumeEvents.push({
                name: "keydown",
                target: element.closest(".o-autocomplete").querySelector("input"),
                conditional: (ev) => ["Tab", "Enter"].includes(ev.key),
            });
        }

        // Press enter on a button do the same as a click
        if (element.tagName === "BUTTON") {
            consumeEvents.push({
                name: "keydown",
                target: element,
                conditional: (ev) => ev.key === "Enter",
            });

            // Pressing enter in the input group does the same as clicking on the button
            if (element.closest(".input-group")) {
                for (const inputEl of element.parentElement.querySelectorAll("input")) {
                    consumeEvents.push({
                        name: "keydown",
                        target: inputEl,
                        conditional: (ev) => ev.key === "Enter",
                    });
                }
            }
        }
    }

    if (["fill", "edit"].includes(runCommand)) {
        if (
            utils.isSmall() &&
            element.closest(".o_field_widget")?.matches(".o_field_many2one, .o_field_many2many")
        ) {
            consumeEvents.push({
                name: "click",
                target: element,
            });
        } else {
            consumeEvents.push({
                name: "input",
                target: element,
            });
        }
    }

    // Drag & drop run command
    if (runCommand === "drag") {
        consumeEvents.push({
            name: "pointerdown",
            target: element,
        });
    }

    if (runCommand === "drop") {
        consumeEvents.push({
            name: "pointerup",
            target: element,
        });
    }

    return consumeEvents;
}
/**
 * @param {HTMLElement} element
 * @returns {HTMLElement | null}
 */
export function getScrollParent(element) {
    if (!element) {
        return null;
    }
    if (element.scrollHeight > element.clientHeight) {
        return element;
    } else {
        return getScrollParent(element.parentNode);
    }
}

export const stepUtils = {
    _getHelpMessage(functionName, ...args) {
        return `Generated by function tour utils ${functionName}(${args.join(", ")})`;
    },

    addDebugHelp(helpMessage, step) {
        if (typeof step.debugHelp === "string") {
            step.debugHelp = step.debugHelp + "\n" + helpMessage;
        } else {
            step.debugHelp = helpMessage;
        }
        return step;
    },

    editionEnterpriseModifier(step) {
        step.edition = "enterprise";
        return step;
    },

    mobileModifier(step) {
        step.isActive = ["mobile"];
        return step;
    },

    showAppsMenuItem() {
        return {
            isActive: ["auto", "community"],
            trigger: ".o_navbar_apps_menu button",
            position: "bottom",
            run: "click",
        };
    },

    toggleHomeMenu() {
        return {
            isActive: ["enterprise"],
            trigger: ".o_main_navbar .o_menu_toggle",
            content: markup(_t("Click on the <i>Home icon</i> to navigate across apps.")),
            position: "bottom",
            run: "click",
        };
    },

    autoExpandMoreButtons() {
        return {
            isActive: ["auto"],
            content: `autoExpandMoreButtons`,
            trigger: ".o-form-buttonbox",
            run() {
                const more = hoot.queryFirst(".o-form-buttonbox .o_button_more");
                if (more) {
                    hoot.click(more);
                }
            },
        };
    },

    goBackBreadcrumbsMobile(description) {
        return [
            {
                isActive: ["mobile"],
                trigger: ".o_back_button",
                content: description,
                position: "bottom",
                run: "click",
            },
        ];
    },

    goToAppSteps(dataMenuXmlid, description) {
        return [
            this.showAppsMenuItem(),
            {
                isActive: ["community"],
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                position: "right",
                run: "click",
            },
            {
                isActive: ["enterprise"],
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                position: "bottom",
                run: "click",
            },
        ].map((step) =>
            this.addDebugHelp(this._getHelpMessage("goToApp", dataMenuXmlid, description), step)
        );
    },

    statusbarButtonsSteps(innerTextButton, description, trigger) {
        const steps = [];
        if (trigger) {
            steps.push({
                isActive: ["auto", "mobile"],
                trigger,
                allowDisabled: true,
            });
        }
        steps.push(
            {
                isActive: ["auto", "mobile"],
                trigger: ".o_statusbar_buttons",
                run: (actions) => {
                    const node = hoot.queryFirst(
                        ".o_statusbar_buttons .btn.dropdown-toggle:contains(Action)"
                    );
                    if (node) {
                        hoot.click(node);
                    }
                },
            },
            {
                trigger: `.o_statusbar_buttons button:enabled:contains('${innerTextButton}'), .dropdown-item button:enabled:contains('${innerTextButton}')`,
                content: description,
                position: "bottom",
                run: "click",
            }
        );
        return steps.map((step) =>
            this.addDebugHelp(
                this._getHelpMessage("statusbarButtonsSteps", innerTextButton, description),
                step
            )
        );
    },

    mobileKanbanSearchMany2X(modalTitle, valueSearched) {
        return [
            {
                isActive: ["mobile"],
                trigger: `.o_control_panel_navigation .btn .fa-search`,
                position: "bottom",
                run: "click",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_searchview_input",
                position: "bottom",
                run: `edit ${valueSearched}`,
            },
            {
                isActive: ["mobile"],
                trigger: ".dropdown-menu.o_searchview_autocomplete",
            },
            {
                isActive: ["mobile"],
                trigger: ".o_searchview_input",
                position: "bottom",
                run: "press Enter",
            },
            {
                isActive: ["mobile"],
                trigger: `.o_kanban_record:contains('${valueSearched}')`,
                position: "bottom",
                run: "click",
            },
        ].map((step) =>
            this.addDebugHelp(
                this._getHelpMessage("mobileKanbanSearchMany2X", modalTitle, valueSearched),
                step
            )
        );
    },
    /**
     * Utility steps to save a form and wait for the save to complete
     */
    saveForm() {
        return [
            {
                isActive: ["auto"],
                content: "save form",
                trigger: ".o_form_button_save",
                run: "click",
            },
            {
                isActive: ["auto"],
                content: "wait for save completion",
                trigger: ".o_form_readonly, .o_form_saved",
            },
        ];
    },
    /**
     * Utility steps to cancel a form creation or edition.
     *
     * Supports creation/edition from either a form or a list view (so checks
     * for both states).
     */
    discardForm() {
        return [
            {
                isActive: ["auto"],
                content: "discard the form",
                trigger: ".o_form_button_cancel",
                run: "click",
            },
            {
                isActive: ["auto"],
                content: "wait for cancellation to complete",
                trigger:
                    ".o_view_controller.o_list_view, .o_form_view > div > div > .o_form_readonly, .o_form_view > div > div > .o_form_saved",
            },
        ];
    },

    waitIframeIsReady() {
        return {
            content: "Wait until the iframe is ready",
            trigger: `iframe[is-ready=true]:iframe html`,
        };
    },
};
