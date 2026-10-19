import { Component, proxy, signal, t, useProps } from "@odoo/owl";
import { omit, pick } from "@web/core/utils/objects";
import { trapFocus } from "@html_editor/utils/dom_traversal";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";

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
            this.focusFirstToolbarButton();
        } else {
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
