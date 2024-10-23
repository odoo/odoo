import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";

export class IconPlugin extends Plugin {
    static name = "icon";
    static dependencies = ["history", "link", "selection", "color"];
    /** @type { (p: IconPlugin) => Record<string, any> } */
    resources = {
        toolbarNamespace: [
            {
                id: "icon",
                isApplied: (traversedNodes) =>
                    traversedNodes.every(
                        (node) =>
                            // All nodes should be icons, its ZWS child or its ancestors
                            node.classList?.contains("fa") ||
                            node.parentElement.classList.contains("fa") ||
                            (node.querySelector?.(".fa") && node.isContentEditable !== false)
                    ),
            },
        ],
        toolbarCategory: [
            withSequence(1, {
                id: "icon_color",
                namespace: "icon",
            }),
            withSequence(1, {
                id: "icon_size",
                namespace: "icon",
            }),
            withSequence(3, { id: "icon_spin", namespace: "icon" }),
        ],
        toolbarItems: [
            {
                id: "icon_forecolor",
                category: "icon_color",
                inherit: "forecolor",
            },
            {
                id: "icon_backcolor",
                category: "icon_color",
                inherit: "backcolor",
            },
            {
                id: "icon_size_1",
                category: "icon_size",
                action(dispatch) {
                    dispatch("RESIZE_ICON", "1");
                },
                text: "1x",
                title: _t("Icon size 1x"),
                isFormatApplied: () => this.hasIconSize("1"),
            },
            {
                id: "icon_size_2",
                category: "icon_size",
                action(dispatch) {
                    dispatch("RESIZE_ICON", "2");
                },
                text: "2x",
                title: _t("Icon size 2x"),
                isFormatApplied: () => this.hasIconSize("2"),
            },
            {
                id: "icon_size_3",
                category: "icon_size",
                action(dispatch) {
                    dispatch("RESIZE_ICON", "3");
                },
                text: "3x",
                title: _t("Icon size 3x"),
                isFormatApplied: () => this.hasIconSize("3"),
            },
            {
                id: "icon_size_4",
                category: "icon_size",
                action(dispatch) {
                    dispatch("RESIZE_ICON", "4");
                },
                text: "4x",
                title: _t("Icon size 4x"),
                isFormatApplied: () => this.hasIconSize("4"),
            },
            {
                id: "icon_size_5",
                category: "icon_size",
                action(dispatch) {
                    dispatch("RESIZE_ICON", "5");
                },
                text: "5x",
                title: _t("Icon size 5x"),
                isFormatApplied: () => this.hasIconSize("5"),
            },
            {
                id: "icon_spin",
                category: "icon_spin",
                action(dispatch) {
                    dispatch("TOGGLE_SPIN_ICON");
                },
                icon: "fa-play",
                title: _t("Toggle icon spin"),
                isFormatApplied: () => this.hasSpinIcon(),
            },
        ],
        colorApply: this.applyIconColor.bind(this),
    };

    getSelectedIcon() {
        const selectedNodes = this.shared.getSelectedNodes();
        return selectedNodes.find((node) => node.classList?.contains?.("fa"));
    }

    handleCommand(command, payload) {
        switch (command) {
            case "RESIZE_ICON": {
                const selectedIcon = this.getSelectedIcon();
                if (!selectedIcon) {
                    return;
                }
                for (const classString of selectedIcon.classList) {
                    if (classString.match(/^fa-[2-5]x$/)) {
                        selectedIcon.classList.remove(classString);
                    }
                }
                if (payload !== "1") {
                    selectedIcon.classList.add(`fa-${payload}x`);
                }
                this.dispatch("ADD_STEP");
                break;
            }
            case "TOGGLE_SPIN_ICON": {
                const selectedIcon = this.getSelectedIcon();
                if (!selectedIcon) {
                    return;
                }
                selectedIcon.classList.toggle("fa-spin");
                break;
            }
        }
    }

    hasIconSize(size) {
        const selectedIcon = this.getSelectedIcon();
        if (!selectedIcon) {
            return;
        }
        if (size === "1") {
            return ![...selectedIcon.classList].some((classString) =>
                classString.match(/^fa-[2-5]x$/)
            );
        }
        return selectedIcon.classList.contains(`fa-${size}x`);
    }

    hasSpinIcon() {
        const selectedIcon = this.getSelectedIcon();
        if (!selectedIcon) {
            return;
        }
        return selectedIcon.classList.contains("fa-spin");
    }

    applyIconColor(color, mode) {
        const selectedIcon = this.getSelectedIcon();
        if (!selectedIcon) {
            return;
        }
        this.shared.colorElement(selectedIcon, color, mode);
        return true;
    }
}
