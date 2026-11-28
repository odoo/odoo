import { Component, onPatched, proxy, signal, t, useProps } from "@odoo/owl";
import { omit, pick } from "@web/core/utils/objects";
import { trapFocus } from "@html_editor/utils/dom_traversal";
import { isMacOS, isMobileOS } from "@web/core/browser/feature_detection";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { _t } from "@web/core/l10n/translation";

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
    isActive: t.boolean(),
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

    setup() {
        this.state = proxy(this.props.state);
        this.shouldFocusFirstButton = false;

        useHotkey("alt+f", () => this.focusFirstToolbarButton(), {
            bypassEditableProtection: true,
            withOverlay: () =>
                document.activeElement.closest(
                    ".o-we-toolbar[data-namespace], [data-prevent-closing-overlay]"
                )
                    ? null
                    : this.toolbarEl(),
            isAvailable: () =>
                !document.activeElement.closest(
                    ".o-we-toolbar[data-namespace], [data-prevent-closing-overlay]"
                ),
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
        // Loop through toolbar buttons
        if (["Tab", "ArrowLeft", "ArrowRight"].includes(ev.key)) {
            ev.preventDefault();
            ev.stopPropagation();
            const toolbarButtons = this.toolbarEl().querySelectorAll("button");
            const isBackward = ev.key === "ArrowLeft" || (ev.key === "Tab" && ev.shiftKey);
            trapFocus(toolbarButtons, isBackward);
        } else if (ev.key === "Escape") {
            ev.stopPropagation();
            this.props.focusEditable();
        }
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

/** @typedef {import("@html_editor/core/user_command_plugin").UserCommand} UserCommand */
/** @typedef {import("./toolbar_plugin").ToolbarCommandItem} ToolbarCommandItem */
/** @typedef {import("./toolbar_plugin").ToolbarCommandButton} ToolbarCommandButton */
/** @typedef {import("@html_editor/core/shortcut_plugin").Shortcut} Shortcut */

/**
 * Returns the description followed by the hotkey, with the key names of the
 * user's OS. Mobile devices have no keyboard shortcuts, so they get the
 * description alone.
 *
 * @param {string} description
 * @param {string} [hotkey] e.g. "control+b"
 * @returns {string}
 */
export function getShortcutTooltip(description, hotkey) {
    if (!hotkey || isMobileOS()) {
        return description;
    }
    const keyNames = {
        control: isMacOS() ? "⌘" : _t("Ctrl"),
        shift: _t("Shift"),
        space: _t("Space"),
    };
    const keys = hotkey.split("+").map((key) => keyNames[key] || key.toUpperCase());
    return `${description} (${keys.join(" + ")})`;
}

/**
 * @param {UserCommand} userCommand
 * @param {ToolbarCommandItem} toolbarItem
 * @param {Shortcut[]} shortcuts
 * @returns {ToolbarCommandButton}
 */
export function composeToolbarButton(userCommand, toolbarItem, shortcuts) {
    const description = toolbarItem.description || userCommand.description;
    const shortcut = shortcuts.find(({ commandId }) => commandId === toolbarItem.commandId);
    return {
        ...pick(userCommand, "icon", "iconClass"),
        ...omit(toolbarItem, "commandId", "commandParams"),
        hotkey: toolbarItem.hotkey ?? shortcut?.hotkey,
        run: () => userCommand.run(toolbarItem.commandParams),
        isAvailable: (selection) =>
            [userCommand.isAvailable, toolbarItem.isAvailable]
                .filter(Boolean)
                .every((predicate) => predicate(selection)),
        description: description instanceof Function ? description : () => description,
    };
}
