// @ts-check
/** @odoo-module native */

import { Component, useExternalListener, useRef, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { hasTouch, isMacOS } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

class FooterComponent extends Component {
    static template = "web.HomeMenu.CommandPalette.Footer";
    static props = {
        switchNamespace: { type: Function, optional: true },
    };

    setup() {
        this.controlKey = isMacOS() ? "COMMAND" : "CONTROL";
    }
}

/** @param {{ onQueryChanged: () => void }} params */
const log = makeLogger("web.webclient.home_menu.search");

export function useHomeMenuSearch({ onQueryChanged }) {
    const command = useService("command");
    const ui = useService("ui");
    const inputRef = useRef("input");
    const state = useState({ query: "" });
    let composing = false;

    /** @returns {HTMLInputElement | null} */
    const inputEl = () => /** @type {HTMLInputElement | null} */ (inputRef.el);

    const search = {
        get query() {
            return state.query;
        },

        get inputEl() {
            return inputEl();
        },

        focus() {
            const el = inputEl();
            if (el && !hasTouch()) {
                el.focus({ preventScroll: true });
            }
        },

        clear() {
            state.query = "";
            const el = inputEl();
            if (el) {
                el.value = "";
            }
            onQueryChanged();
        },

        onInput() {
            if (composing) {
                return;
            }
            const typed = inputEl()?.value.trim() ?? "";
            const namespaced =
                typed.length > 0 &&
                registry.category("command_setup").contains(typed[0]);
            if (!namespaced) {
                state.query = typed;
                onQueryChanged();
                return;
            }
            search.clear();
            handOverToPalette(command, typed, () => search.focus());
        },

        openPalette() {
            handOverToPalette(command, `/${state.query}`, () => search.focus());
        },

        /** @param {FocusEvent} [ev] */
        onBlur(ev) {
            if (hasTouch()) {
                return;
            }
            const target = ev?.relatedTarget;
            const focusedElsewhere = Boolean(target) && target !== document.body;
            browser.setTimeout(() => {
                const refocus =
                    !focusedElsewhere &&
                    document.activeElement === document.body &&
                    ui.activeElement === document;
                log.logic("blur", () => ({
                    refocus,
                    focusedElsewhere,
                    relatedTarget: target?.outerHTML?.slice(0, 80) ?? null,
                    activeElement: document.activeElement?.tagName,
                    uiActiveElement:
                        ui.activeElement === document ? "document" : "overlay",
                }));
                if (refocus) {
                    search.focus();
                }
            });
        },

        onCompositionStart() {
            composing = true;
        },
        onCompositionEnd() {
            composing = false;
            search.onInput();
        },
    };

    useTypeToFocus(inputRef, ui, () => search.focus());

    return search;
}

/**
 * @param {import("services").ServiceFactories["command"]} command
 * @param {string} searchValue
 * @param {() => void} refocus
 */
function handOverToPalette(command, searchValue, refocus) {
    command.openMainPalette(
        /** @type {any} */ ({ searchValue, FooterComponent }),
        refocus,
    );
}

/**
 * @param {import("@odoo/owl").Ref<HTMLElement>} inputRef
 * @param {import("services").ServiceFactories["ui"]} ui
 * @param {() => void} focus
 */
function useTypeToFocus(inputRef, ui, focus) {
    useExternalListener(window, "keydown", (/** @type {KeyboardEvent} */ ev) => {
        const printable =
            ev.key.length === 1 && !ev.ctrlKey && !ev.metaKey && !ev.altKey;
        if (
            printable &&
            document.activeElement !== inputRef.el &&
            ui.activeElement === document &&
            !["TEXTAREA", "INPUT", "SELECT"].includes(
                document.activeElement?.tagName ?? "",
            ) &&
            !document.activeElement?.closest("[contenteditable=true]")
        ) {
            focus();
        }
    });
}
