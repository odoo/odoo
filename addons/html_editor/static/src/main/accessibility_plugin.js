import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { AccessibilityDialog } from "./accessibility_dialog";

export class AccessibilityPlugin extends Plugin {
    static id = "accessibility";
    static dependencies = ["dialog", "selection", "userCommand"];
    static defaultConfig = { accessibilityDialog: false };

    resources = {
        user_commands: [
            {
                id: "accessibility",
                title: _t("Accessibility help"),
                description: _t("View keyboard shortcuts and typing shorthands"),
                icon: "accessibility",
                isAvailable: () => this.config.accessibilityDialog,
                run: () => this.openDialog(),
            },
        ],
        powerbox_categories: withSequence(20, {
            id: "accessibility",
            name: _t("Accessibility"),
        }),
        powerbox_items: [{ categoryId: "accessibility", commandId: "accessibility" }],
    };

    setup() {
        this.unregisterCommandCallback = this.services.command?.add(
            _t("Editor accessibility"),
            () => {
                const selection = this.dependencies.selection.getEditableSelection();
                setTimeout(() => this.openDialog(selection));
            },
            {
                isAvailable: () => this.config.accessibilityDialog,
            }
        );
    }

    destroy() {
        this.unregisterCommandCallback?.();
        super.destroy();
    }

    openDialog(selection = this.dependencies.selection.getEditableSelection()) {
        return this.dependencies.dialog.addDialog(AccessibilityDialog, {
            shortcuts: this.getShortcuts(selection),
            shorthands: this.getResource("shorthands")
                .filter((shorthand) => this.isAvailable(shorthand, selection))
                .map(({ label, literals, inline }) => ({
                    label,
                    literals,
                    inline: !!inline,
                })),
        });
    }

    isAvailable({ label, commandId }, selection) {
        if (!label || !commandId) {
            return Boolean(label);
        }
        const command = this.dependencies.userCommand.getCommand(commandId);
        return !command.isAvailable || command.isAvailable(selection);
    }

    getShortcuts(selection) {
        const categories = new Map();
        for (const shortcut of this.getResource("shortcuts")) {
            if (!this.isAvailable(shortcut, selection)) {
                continue;
            }
            const { label, category = _t("Other"), hotkey } = shortcut;
            if (!categories.has(category)) {
                categories.set(category, new Map());
            }
            const rows = categories.get(category);
            const row = rows.get(label) ?? { label, keyCombinations: [] };
            row.keyCombinations.push(this.formatKeys(hotkey));
            rows.set(label, row);
        }
        return [...categories].map(([category, rows]) => ({
            category,
            shortcuts: [...rows.values()],
        }));
    }

    formatKeys(hotkey) {
        const keyNames = {
            control: _t("Ctrl"),
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
}
