import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { AccessibilityDialog } from "./accessibility_dialog";
import { isMacOS } from "@web/core/browser/feature_detection";

export class AccessibilityPlugin extends Plugin {
    static id = "accessibility";
    static dependencies = ["dialog", "selection", "userCommand"];

    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "openAccessibilityDialog",
                title: _t("Accessibility help"),
                description: _t("View keyboard shortcuts and typing shorthands"),
                icon: "accessibility",
                run: () => this.openDialog(),
            },
        ],
        powerbox_categories: {
            id: "accessibility",
            name: _t("Accessibility"),
        },
        powerbox_items: [
            {
                categoryId: "accessibility",
                commandId: "openAccessibilityDialog",
                keywords: [_t("hotkeys"), _t("shortcuts")],
            },
        ],
    };

    setup() {
        this.unregisterCommandCallback = this.services.command?.add(
            _t("Accessibility help"),
            () => {
                // Wait for the command palette to close before opening the dialog
                // to avoid a race between restoring focus and focusing the dialog.
                setTimeout(() => this.openDialog());
            }
        );
    }

    openDialog() {
        return this.dependencies.dialog.addDialog(AccessibilityDialog, {
            shortcuts: this.getShortcuts(),
            shorthands: this.getShorthands(),
        });
    }

    getShortcuts() {
        const categories = this.getResource("shortcut_categories");
        const shortcutCategories = new Map(categories.map(({ id }) => [id, new Map()]));
        for (const { commandId, categoryId, hotkey } of this.getResource("shortcuts")) {
            const shortcutsByTitle = shortcutCategories.get(categoryId);
            const command = this.dependencies.userCommand.getCommand(commandId);
            if (!shortcutsByTitle || !command.title) {
                continue;
            }
            const shortcut = shortcutsByTitle.get(command.title) ?? {
                title: command.title,
                keyCombinations: [],
            };
            shortcut.keyCombinations.push(this.formatKeys(hotkey));
            shortcutsByTitle.set(command.title, shortcut);
        }

        return categories
            .filter(({ id }) => shortcutCategories.get(id).size)
            .map(({ id, name }) => ({
                category: name,
                shortcuts: [...shortcutCategories.get(id).values()],
            }));
    }

    getShorthands() {
        const shorthands = [];
        for (const { commandId, title: shorthandTitle, literals, inline } of this.getResource("shorthands")) {
            const command = this.dependencies.userCommand.getCommand(commandId);
            const title = shorthandTitle ?? command.title;
            if (title) {
                shorthands.push({ title, literals, inline: !!inline });
            }
        }
        return shorthands;
    }

    formatKeys(hotkey) {
        const keyNames = {
            control: isMacOS() ? "⌘" : _t("Ctrl"),
            alt: _t("Alt"),
            shift: _t("Shift"),
            escape: _t("Esc"),
            arrowleft: "←",
            arrowright: "→",
            arrowup: "↑",
            arrowdown: "↓",
            pageup: _t("Page Up"),
            pagedown: _t("Page Down"),
            space: _t("Space"),
            backspace: _t("Backspace"),
            delete: _t("Delete"),
            tab: _t("Tab"),
            enter: _t("Enter"),
        };
        return hotkey.split("+").map((key) => keyNames[key.toLowerCase()] || key.toUpperCase());
    }

    destroy() {
        this.unregisterCommandCallback?.();
        super.destroy();
    }
}
