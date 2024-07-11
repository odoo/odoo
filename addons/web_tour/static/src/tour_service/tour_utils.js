/** @odoo-module **/

import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { utils } from "@web/core/ui/ui_service";
import { _legacyIsVisible } from "@web/core/utils/ui";

/**
 * @typedef {string | (actions: RunningTourActionHelper) => void | Promise<void>} RunCommand
 */

export class TourError extends Error {
    constructor(message, ...args) {
        super(message, ...args);
        this.message = `(TourError) ${message}`;
    }
}

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

export function getFirstVisibleElement($elements) {
    for (var i = 0; i < $elements.length; i++) {
        var $i = $elements.eq(i);
        if (_legacyIsVisible($i[0])) {
            return $i;
        }
    }
    return $();
}

/**
 * @param {JQuery|undefined} target
 */
export function getJQueryElementFromSelector(selector, $target) {
    $target = $target || $(document);
    const iframeSplit = typeof selector === "string" && selector.match(/(.*\biframe[^ ]*)(.*)/);
    if (iframeSplit && iframeSplit[2]) {
        var $iframe = $target.find(`${iframeSplit[1]}:not(.o_ignore_in_tour)`);
        if ($iframe.is('[is-ready="false"]')) {
            return $();
        }
        var $el = $iframe.contents().find(iframeSplit[2]);
        $el.iframeContainer = $iframe[0];
        return $el;
    } else if (typeof selector === "string") {
        return $target.find(selector);
    } else {
        return $(selector);
    }
}

/**
 * @param {HTMLElement} [element]
 * @param {RunCommand} [runCommand]
 * @returns {string}
 */
export function getConsumeEventType(element, runCommand) {
    if (!element) {
        return "click";
    }
    const { classList, tagName, type } = element;
    const tag = tagName.toLowerCase();

    // Many2one
    if (classList.contains("o_field_many2one")) {
        return "autocompleteselect";
    }

    // Inputs and textareas
    if (
        tag === "textarea" ||
        (tag === "input" &&
            (!type ||
                ["email", "number", "password", "search", "tel", "text", "url"].includes(type)))
    ) {
        if (
            utils.isSmall() &&
            element.closest(".o_field_widget")?.matches(".o_field_many2one, .o_field_many2many")
        ) {
            return "click";
        }
        return "input";
    }

    // jQuery draggable
    if (classList.contains("ui-draggable-handle")) {
        return "mousedown";
    }

    // Drag & drop run command
    if (typeof runCommand === "string" && /^drag_and_drop/.test(runCommand)) {
        // this is a heuristic: the element has to be dragged and dropped but it
        // doesn't have class 'ui-draggable-handle', so we check if it has an
        // ui-sortable parent, and if so, we conclude that its event type is 'sort'
        if (element.closest(".ui-sortable")) {
            return "sort";
        }
        if (
            (/^drag_and_drop_native/.test(runCommand) && classList.contains("o_draggable")) ||
            element.closest(".o_draggable")
        ) {
            return "pointerdown";
        }
    }

    // Default: click
    return "click";
}

/**
 * ! This function is a copy-paste of its namesake in web/static/tests/helpers/utils.js
 * TODO: Unify utils for tests and tours since they're doing the exact same thing
 * @param {Node} n1
 * @param {Node} n2
 * @returns {Node[]}
 */
export function getDifferentParents(n1, n2) {
    const parents = [n2];
    while (parents[0].parentNode) {
        const parent = parents[0].parentNode;
        if (parent.contains(n1)) {
            break;
        }
        parents.unshift(parent);
    }
    return parents;
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

/**
 * @param {HTMLElement} el
 * @param {string} type
 * @param {boolean} canBubbleAndBeCanceled
 * @param {PointerEventInit} [additionalParams]
 */
export const triggerPointerEvent = (el, type, canBubbleAndBeCanceled, additionalParams) => {
    const eventInit = {
        bubbles: canBubbleAndBeCanceled,
        cancelable: canBubbleAndBeCanceled,
        view: window,
        ...additionalParams,
    };

    el.dispatchEvent(new PointerEvent(type, eventInit));
    if (type.startsWith("pointer")) {
        el.dispatchEvent(new MouseEvent(type.replace("pointer", "mouse"), eventInit));
    }
};

export class RunningTourActionHelper {
    constructor(tip_widget) {
        this.tip_widget = tip_widget;
    }
    click(element) {
        this._click(this._get_action_values(element));
    }
    dblclick(element) {
        this._click(this._get_action_values(element), 2);
    }
    tripleclick(element) {
        this._click(this._get_action_values(element), 3);
    }
    clicknoleave(element) {
        this._click(this._get_action_values(element), 1, false);
    }
    text(text, element) {
        this._text(this._get_action_values(element), text);
    }
    remove_text(text, element) {
        this._text(this._get_action_values(element), "\n");
    }
    text_blur(text, element) {
        this._text_blur(this._get_action_values(element), text);
    }
    range(text, element) {
        this._range(this._get_action_values(element), text);
    }
    drag_and_drop(to, element) {
        this._drag_and_drop_jquery(this._get_action_values(element), to);
    }
    drag_and_drop_native(toSel, element) {
        const to = getJQueryElementFromSelector(toSel)[0];
        this._drag_and_drop(this._get_action_values(element).$element[0], to);
    }
    keydown(keyCodes, element) {
        this._keydown(this._get_action_values(element), keyCodes.split(/[,\s]+/));
    }
    auto(element) {
        var values = this._get_action_values(element);
        if (values.consume_event === "input") {
            this._text(values);
        } else {
            this._click(values);
        }
    }
    _get_action_values(element) {
        var $e = getJQueryElementFromSelector(element);
        var $element = element ? getFirstVisibleElement($e) : this.tip_widget.$anchor;
        if ($element.length === 0) {
            $element = $e.first();
        }
        var consume_event = element
            ? getConsumeEventType($element[0])
            : this.tip_widget.consume_event;
        return {
            $element: $element,
            consume_event: consume_event,
        };
    }
    _click(values, nb, leave) {
        const target = values.$element[0];
        triggerPointerEvent(target, "pointerover", true);
        triggerPointerEvent(target, "pointerenter", false);
        triggerPointerEvent(target, "pointermove", true);
        for (let i = 1; i <= (nb || 1); i++) {
            triggerPointerEvent(target, "pointerdown", true);
            triggerPointerEvent(target, "pointerup", true);
            triggerPointerEvent(target, "click", true, { detail: i });
            if (i % 2 === 0) {
                triggerPointerEvent(target, "dblclick", true);
            }
        }
        if (leave !== false) {
            triggerPointerEvent(target, "pointerout", true);
            triggerPointerEvent(target, "pointerleave", false);
        }
    }
    _text(values, text) {
        this._click(values);

        text = text || "Test";
        if (values.consume_event === "input") {
            values.$element
                .trigger({ type: "keydown", key: text[text.length - 1] })
                .val(text)
                .trigger({ type: "keyup", key: text[text.length - 1] });
            values.$element[0].dispatchEvent(
                new InputEvent("input", {
                    bubbles: true,
                })
            );
        } else if (values.$element.is("select")) {
            var $options = values.$element.find("option");
            $options.prop("selected", false).removeProp("selected");
            var $selectedOption = $options.filter(function () {
                return $(this).val() === text;
            });
            if ($selectedOption.length === 0) {
                $selectedOption = $options.filter(function () {
                    return $(this).text().trim() === text;
                });
            }
            const regex = /option\s+([0-9]+)/;
            if ($selectedOption.length === 0 && regex.test(text)) {
                // Extract position as 1-based, as the nth selectors.
                const position = parseInt(regex.exec(text)[1]);
                $selectedOption = $options.eq(position - 1); // eq is 0-based.
            }
            $selectedOption.prop("selected", true);
            this._click(values);
            // For situations where an `oninput` is defined.
            values.$element.trigger("input");
        } else {
            values.$element.focusIn();
            values.$element.trigger($.Event("keydown", { key: "_" }));
            values.$element.text(text).trigger("input");
            values.$element.focusInEnd();
            values.$element.trigger($.Event("keyup", { key: "_" }));
        }
        values.$element[0].dispatchEvent(new Event("change", { bubbles: true, cancelable: false }));
    }
    _text_blur(values, text) {
        this._text(values, text);
        values.$element.trigger("focusout");
        values.$element.trigger("blur");
    }
    _range(values, text) {
        values.$element[0].value = text;
        values.$element[0].dispatchEvent(new Event('change', { bubbles: true, cancelable: false }));
    }
    _calculateCenter($el, selector) {
        const center = $el.offset();
        if (selector && selector.indexOf("iframe") !== -1) {
            const iFrameOffset = $("iframe").offset();
            center.left += iFrameOffset.left;
            center.top += iFrameOffset.top;
        }
        center.left += $el.outerWidth() / 2;
        center.top += $el.outerHeight() / 2;
        return center;
    }
    _drag_and_drop_jquery(values, to) {
        var $to;
        const elementCenter = this._calculateCenter(values.$element);
        if (to) {
            $to = getJQueryElementFromSelector(to);
        } else {
            $to = $(document.body);
        }

        values.$element.trigger($.Event("mouseenter"));
        // Make the web_studio tour test happy. My guess is that 50%+ of the length of the dragged element
        // must be situated to the right of the $to element.
        values.$element.trigger(
            $.Event("mousedown", {
                which: 1,
                pageX: elementCenter.left + 1,
                pageY: elementCenter.top,
            })
        );
        // Some tests depends on elements present only when the element to drag
        // start to move while some other tests break while moving.
        if (!$to.length) {
            values.$element.trigger(
                $.Event("mousemove", {
                    which: 1,
                    pageX: elementCenter.left + 1,
                    pageY: elementCenter.top,
                })
            );
            $to = getJQueryElementFromSelector(to);
        }

        let toCenter = this._calculateCenter($to, to);
        values.$element.trigger(
            $.Event("mousemove", { which: 1, pageX: toCenter.left, pageY: toCenter.top })
        );
        // Recalculate the center as the mousemove might have made the element bigger.
        toCenter = this._calculateCenter($to, to);
        values.$element.trigger(
            $.Event("mouseup", { which: 1, pageX: toCenter.left, pageY: toCenter.top })
        );
    }
    /**
     * ! This function is a reduced version of "drag" in web/static/tests/helpers/utils.js
     * TODO: Unify utils for tests and tours since they're doing the exact same thing
     * @param {HTMLElement} source
     * @param {HTMLElement} target
     */
    _drag_and_drop(source, target) {
        const sourceRect = source.getBoundingClientRect();
        const sourcePosition = {
            clientX: sourceRect.x + sourceRect.width / 2,
            clientY: sourceRect.y + sourceRect.height / 2,
        };

        const targetRect = target.getBoundingClientRect();
        const targetPosition = {
            clientX: targetRect.x + targetRect.width / 2,
            clientY: targetRect.y + targetRect.height / 2,
        };

        triggerPointerEvent(source, "pointerdown", true, sourcePosition);
        triggerPointerEvent(source, "pointermove", true, targetPosition);

        for (const parent of getDifferentParents(source, target)) {
            triggerPointerEvent(parent, "pointerenter", false, targetPosition);
        }

        triggerPointerEvent(target, "pointerup", true, targetPosition);
    }
    _keydown(values, keyCodes) {
        while (keyCodes.length) {
            const eventOptions = {};
            const keyCode = keyCodes.shift();
            let insertedText = null;
            if (isNaN(keyCode)) {
                eventOptions.key = keyCode;
            } else {
                const code = parseInt(keyCode, 10);
                if (
                    code === 32 || // spacebar
                    (code > 47 && code < 58) || // number keys
                    (code > 64 && code < 91) || // letter keys
                    (code > 95 && code < 112) || // numpad keys
                    (code > 185 && code < 193) || // ;=,-./` (in order)
                    (code > 218 && code < 223) // [\]' (in order))
                ) {
                    insertedText = String.fromCharCode(code);
                }
            }
            values.$element.trigger(Object.assign({ type: "keydown" }, eventOptions));
            if (insertedText) {
                values.$element[0].ownerDocument.execCommand("insertText", 0, insertedText);
            }
            values.$element.trigger(Object.assign({ type: "keyup" }, eventOptions));
        }
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
        step.mobile = true;
        return step;
    },

    showAppsMenuItem() {
        return {
            edition: "community",
            trigger: ".o_navbar_apps_menu button",
            auto: true,
            position: "bottom",
        };
    },

    toggleHomeMenu() {
        return {
            edition: "enterprise",
            trigger: ".o_main_navbar .o_menu_toggle",
            content: markup(_t("Click on the <i>Home icon</i> to navigate across apps.")),
            position: "bottom",
        };
    },

    autoExpandMoreButtons(extra_trigger) {
        return {
            trigger: ".o-form-buttonbox",
            extra_trigger: extra_trigger,
            auto: true,
            run: (actions) => {
                const $more = $(".o-form-buttonbox .o_button_more");
                if ($more.length) {
                    actions.click($more);
                }
            },
        };
    },

    goBackBreadcrumbsMobile(description, ...extraTrigger) {
        return extraTrigger.map((element) => ({
            mobile: true,
            trigger: ".o_back_button",
            extra_trigger: element,
            content: description,
            position: "bottom",
            debugHelp: this._getHelpMessage(
                "goBackBreadcrumbsMobile",
                description,
                ...extraTrigger
            ),
        }));
    },

    goToAppSteps(dataMenuXmlid, description) {
        return [
            this.showAppsMenuItem(),
            {
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                position: "right",
                edition: "community",
            },
            {
                trigger: `.o_app[data-menu-xmlid="${dataMenuXmlid}"]`,
                content: description,
                position: "bottom",
                edition: "enterprise",
            },
        ].map((step) =>
            this.addDebugHelp(this._getHelpMessage("goToApp", dataMenuXmlid, description), step)
        );
    },

    openBurgerMenu(extraTrigger) {
        return {
            mobile: true,
            trigger: ".o_mobile_menu_toggle",
            extra_trigger: extraTrigger,
            content: _t("Open bugger menu."),
            position: "bottom",
            debugHelp: this._getHelpMessage("openBurgerMenu", extraTrigger),
        };
    },

    statusbarButtonsSteps(innerTextButton, description, extraTrigger) {
        return [
            {
                mobile: true,
                auto: true,
                trigger: ".o_statusbar_buttons",
                extra_trigger: extraTrigger,
                run: (actions) => {
                    const $action = $(".o_statusbar_buttons .btn.dropdown-toggle:contains(Action)");
                    if ($action.length) {
                        actions.click($action);
                    }
                },
            },
            {
                trigger: `.o_statusbar_buttons button:enabled:contains('${innerTextButton}')`,
                content: description,
                position: "bottom",
            },
        ].map((step) =>
            this.addDebugHelp(
                this._getHelpMessage(
                    "statusbarButtonsSteps",
                    innerTextButton,
                    description,
                    extraTrigger
                ),
                step
            )
        );
    },

    simulateEnterKeyboardInSearchModal() {
        return {
            mobile: true,
            trigger: ".o_searchview_input",
            extra_trigger: ".modal:not(.o_inactive_modal) .dropdown-menu.o_searchview_autocomplete",
            position: "bottom",
            run: (action) => {
                const keyEventEnter = new KeyboardEvent("keydown", {
                    bubbles: true,
                    cancelable: true,
                    key: "Enter",
                    code: "Enter",
                });
                action.tip_widget.$anchor[0].dispatchEvent(keyEventEnter);
            },
            debugHelp: this._getHelpMessage("simulateEnterKeyboardInSearchModal"),
        };
    },

    mobileKanbanSearchMany2X(modalTitle, valueSearched) {
        return [
            {
                mobile: true,
                trigger: `.o_control_panel_navigation .btn .fa-search`,
                position: "bottom",
            },
            {
                mobile: true,
                trigger: ".o_searchview_input",
                extra_trigger: `.modal:not(.o_inactive_modal) .modal-title:contains('${modalTitle}')`,
                position: "bottom",
                run: `text ${valueSearched}`,
            },
            this.simulateEnterKeyboardInSearchModal(),
            {
                mobile: true,
                trigger: `.o_kanban_record .o_kanban_record_title :contains('${valueSearched}')`,
                position: "bottom",
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
     *
     * @param {object} [options]
     * @param {string} [options.content]
     * @param {string} [options.extra_trigger] additional save-condition selector
     */
    saveForm(options = {}) {
        return [
            {
                content: options.content || "save form",
                trigger: ".o_form_button_save",
                extra_trigger: options.extra_trigger,
                run: "click",
                auto: true,
            },
            {
                content: "wait for save completion",
                trigger: ".o_form_readonly, .o_form_saved",
                run() {},
                auto: true,
            },
        ];
    },
    /**
     * Utility steps to cancel a form creation or edition.
     *
     * Supports creation/edition from either a form or a list view (so checks
     * for both states).
     */
    discardForm(options = {}) {
        return [
            {
                content: options.content || "exit the form",
                trigger: ".o_form_button_cancel",
                extra_trigger: options.extra_trigger,
                run: "click",
                auto: true,
            },
            {
                content: "wait for cancellation to complete",
                trigger:
                    ".o_view_controller.o_list_view, .o_form_view > div > div > .o_form_readonly, .o_form_view > div > div > .o_form_saved",
                run() {},
                auto: true,
            },
        ];
    },
};
