import { Component, onPatched, proxy, signal, t, useProps } from "@odoo/owl";
import { omit, pick } from "@web/core/utils/objects";
import { trapFocus } from "@html_editor/utils/dom_traversal";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";
import { useFocusTooltip } from "@html_editor/toolbar_dropdown_hook";

const componentButtonSchema = {
    Component: t.component(),
    description: t.string(),
    id: t.string(),
    isDisabled: t.boolean(),
    props: t.object().optional(),
};

const genericButtonSchema = {
    description: t.string(),
    icon: t.string().optional(),
    iconClass: t.string().optional(),
    id: t.string(),
    isActive: t.boolean().optional(),
    isDisabled: t.boolean(),
    opensUi: t.boolean().optional(),
    run: t.function(),
    text: t.string().optional(),
};

export class Toolbar extends Component {
    static template = "html_editor.Toolbar";
    props = useProps({
        class: t.string().optional(),
        getSelection: t.function(),
        focusEditable: t.function(),
        state: t.object({
            namespace: t.string().optional(),
            buttonGroups: t.array(
                t.object({
                    id: t.string(),
                    buttons: t.array(
                        t.or([t.object(componentButtonSchema), t.object(genericButtonSchema)])
                    ),
                })
            ),
        }),
    });

    toolbarEl = signal.ref();
    ariaLabel = _t("HTML editor toolbar");

    setup() {
        this.state = proxy(this.props.state);
        this.shouldFocusFirstButton = false;
        useFocusTooltip(this.toolbarEl);

        const isFocusOutsideToolbar = () =>
            !document.activeElement.closest(
                ".o-we-toolbar[data-namespace], [data-prevent-closing-overlay]"
            );
        // Alt+F10 is the usual shortcut to reach an editor toolbar, and is the
        // one displayed in the hotkey overlay. Alt+F is kept as an alias, as
        // Alt+F10 is caught by some window managers (e.g. GNOME).
        useHotkey("alt+f10", () => this.focusFirstToolbarButton(), {
            bypassEditableProtection: true,
            withOverlay: () => (isFocusOutsideToolbar() ? this.toolbarEl() : null),
            isAvailable: isFocusOutsideToolbar,
        });
        useHotkey("alt+f", () => this.focusFirstToolbarButton(), {
            bypassEditableProtection: true,
            isAvailable: isFocusOutsideToolbar,
        });

        onPatched(() => {
            if (this.shouldFocusFirstButton) {
                this.shouldFocusFirstButton = false;
                this.focusFirstToolbarButton();
            }
        });
    }

    focusFirstToolbarButton() {
        this.toolbarEl()?.querySelector("button:not([disabled])").focus();
    }

    onKeyDown(ev) {
        const isDropdownOpen = ev.target.closest(".dropdown.show");
        if (isDropdownOpen) {
            return;
        }
        if (["ArrowLeft", "ArrowRight", "Home", "End", "Tab"].includes(ev.key)) {
            ev.preventDefault();
            ev.stopPropagation();
        }
        // Arrows move between buttons, Home and End to the first and last
        // ones, and Tab between button groups, as a toolbar is navigated
        // with arrows rather than with Tab.
        if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") {
            trapFocus(this.getFocusableButtons(this.toolbarEl()), ev.key === "ArrowLeft");
        } else if (ev.key === "Home" || ev.key === "End") {
            const buttons = this.getFocusableButtons(this.toolbarEl());
            buttons.at(ev.key === "Home" ? 0 : -1)?.focus();
        } else if (ev.key === "Tab") {
            this.focusAdjacentButtonGroup(ev.shiftKey);
        } else if (ev.key === "Escape") {
            ev.stopPropagation();
            this.props.focusEditable();
        }
    }

    /**
     * @param {HTMLElement} el
     * @returns {HTMLButtonElement[]}
     */
    getFocusableButtons(el) {
        return [...el.querySelectorAll("button:not([disabled])")];
    }

    /**
     * Moves the focus to the first button of the next (or previous) button
     * group, cycling through the groups and skipping the ones without any
     * enabled button.
     *
     * @param {boolean} backward
     */
    focusAdjacentButtonGroup(backward) {
        const groups = [...this.toolbarEl().querySelectorAll(":scope > .btn-group")].filter(
            (group) => this.getFocusableButtons(group).length
        );
        if (!groups.length) {
            return;
        }
        const currentIndex = groups.findIndex((group) => group.contains(document.activeElement));
        const nextIndex =
            currentIndex === -1
                ? backward
                    ? groups.length - 1
                    : 0
                : (currentIndex + (backward ? -1 : 1) + groups.length) % groups.length;
        this.getFocusableButtons(groups[nextIndex])[0].focus();
    }

    onButtonClick(button) {
        button.run();
        if (button.id === "expand_toolbar") {
            // Toolbar update is async, defer focus until after OWL re-renders the DOM.
            this.shouldFocusFirstButton = true;
        } else if (!button.opensUi) {
            this.props.focusEditable();
        }
    }
}

export const toolbarButtonProps = {
    title: t.or([t.string(), t.function()]),
    getSelection: t.function(),
    isDisabled: t.boolean(),
};

/**
 * Builds the `aria-label` of a toolbar button, including its current value
 * when relevant (e.g. "Select text style: Paragraph"), so that screen readers
 * announce it while the visible text remains part of the accessible name.
 *
 * @param {string} title
 * @param {string|number} [value]
 * @returns {string}
 */
export function getToolbarAriaLabel(title, value) {
    if (value === undefined || value === null || value === "") {
        return title;
    }
    return _t("%(label)s: %(value)s", { label: title, value });
}

/** @typedef {import("@html_editor/core/user_command_plugin").UserCommand} UserCommand */
/** @typedef {import("./toolbar_plugin").ToolbarCommandItem} ToolbarCommandItem */
/** @typedef {import("./toolbar_plugin").ToolbarCommandButton} ToolbarCommandButton */

/**
 * @param {UserCommand} userCommand
 * @param {ToolbarCommandItem} toolbarItem
 * @returns {ToolbarCommandButton}
 */
export function composeToolbarButton(userCommand, toolbarItem) {
    const description = toolbarItem.description || userCommand.description;
    return {
        ...pick(userCommand, "icon", "iconClass"),
        ...omit(toolbarItem, "commandId", "commandParams"),
        run: () => userCommand.run(toolbarItem.commandParams),
        isAvailable: (selection) =>
            [userCommand.isAvailable, toolbarItem.isAvailable]
                .filter(Boolean)
                .every((predicate) => predicate(selection)),
        description: description instanceof Function ? description : () => description,
    };
}
