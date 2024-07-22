import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";

export class IconPlugin extends Plugin {
    static name = "icon";
    static dependencies = ["history", "link", "selection"];

    static resources(p) {
        return {
            toolbarNamespace: [
                {
                    id: "icon",
                    isApplied: (traversedNodes) => {
                        return traversedNodes?.[0]?.classList?.contains("fa");
                    },
                },
            ],
            toolbarGroup: [
                {
                    id: "icon_size",
                    sequence: 1,
                    namespace: "icon",
                    buttons: [
                        {
                            id: "icon_size_1",
                            action(dispatch) {
                                dispatch("RESIZE_ICON", "1");
                            },
                            text: "1x",
                            name: _t("Icon size 1x"),
                            isFormatApplied: () => p.hasIconSize("1"),
                        },
                        {
                            id: "icon_size_2",
                            action(dispatch) {
                                dispatch("RESIZE_ICON", "2");
                            },
                            text: "2x",
                            name: _t("Icon size 2x"),
                            isFormatApplied: () => p.hasIconSize("2"),
                        },
                        {
                            id: "icon_size_3",
                            action(dispatch) {
                                dispatch("RESIZE_ICON", "3");
                            },
                            text: "3x",
                            name: _t("Icon size 3x"),
                            isFormatApplied: () => p.hasIconSize("3"),
                        },
                        {
                            id: "icon_size_4",
                            action(dispatch) {
                                dispatch("RESIZE_ICON", "4");
                            },
                            text: "4x",
                            name: _t("Icon size 4x"),
                            isFormatApplied: () => p.hasIconSize("4"),
                        },
                        {
                            id: "icon_size_5",
                            action(dispatch) {
                                dispatch("RESIZE_ICON", "5");
                            },
                            text: "5x",
                            name: _t("Icon size 5x"),
                            isFormatApplied: () => p.hasIconSize("5"),
                        },
                    ],
                },
            ],
        };
    }

    getSelectedIcon() {
        const selectedNodes = this.shared.getSelectedNodes();
        return selectedNodes.find((node) => node.classList?.contains?.("fa"));
    }

    handleCommand(command, payload) {
        switch (command) {
            case "RESIZE_ICON":
                {
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
                }
                break;
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
}
