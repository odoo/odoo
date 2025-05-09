import { withSequence } from "@html_editor/utils/resource";
import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { ColorSelector } from "../font/color_selector";
import { MediaDialog } from "./media_dialog/media_dialog";

export class IconPlugin extends Plugin {
    static id = "icon";
    static dependencies = ["history", "selection", "color", "dialog"];
    resources = {
        user_commands: [
            {
                id: "resizeIcon1",
                title: _t("Icon size 1x"),
                run: () => this.resizeIcon({ size: "1" }),
            },
            {
                id: "resizeIcon2",
                title: _t("Icon size 2x"),
                run: () => this.resizeIcon({ size: "2" }),
            },
            {
                id: "resizeIcon3",
                title: _t("Icon size 3x"),
                run: () => this.resizeIcon({ size: "3" }),
            },
            {
                id: "resizeIcon4",
                title: _t("Icon size 4x"),
                run: () => this.resizeIcon({ size: "4" }),
            },
            {
                id: "resizeIcon5",
                title: _t("Icon size 5x"),
                run: () => this.resizeIcon({ size: "5" }),
            },
            {
                id: "toggleSpinIcon",
                title: _t("Toggle icon spin"),
                icon: "fa-play",
                run: this.toggleSpinIcon.bind(this),
            },
            {
                id: "replaceIcon",
                title: _t("Replace icon"),
                run: this.openIconDialog.bind(this),
            },
        ],
        toolbar_namespaces: [
            {
                id: "icon",
                isApplied: (targetedNodes) =>
                    targetedNodes.every(
                        (node) =>
                            // All nodes should be icons, its ZWS child or its ancestors
                            node.classList?.contains("fa") ||
                            node.parentElement.classList.contains("fa") ||
                            (node.querySelector?.(".fa") && node.isContentEditable !== false)
                    ),
            },
        ],
        toolbar_groups: [
            withSequence(1, {
                id: "icon_color",
                namespace: "icon",
            }),
            withSequence(1, {
                id: "icon_size",
                namespace: "icon",
            }),
            withSequence(3, { id: "icon_spin", namespace: "icon" }),
            withSequence(3, { id: "icon_replace", namespace: "icon" }),
        ],
        toolbar_items: [
            {
                id: "icon_forecolor",
                groupId: "icon_color",
                title: _t("Font Color"),
                Component: ColorSelector,
                props: this.dependencies.color.getPropsForColorSelector("foreground"),
            },
            {
                id: "icon_backcolor",
                groupId: "icon_color",
                title: _t("Background Color"),
                Component: ColorSelector,
                props: this.dependencies.color.getPropsForColorSelector("background"),
            },
            {
                id: "icon_size_1",
                groupId: "icon_size",
                commandId: "resizeIcon1",
                text: "1x",
                isActive: () => this.hasIconSize("1"),
            },
            {
                id: "icon_size_2",
                groupId: "icon_size",
                commandId: "resizeIcon2",
                text: "2x",
                isActive: () => this.hasIconSize("2"),
            },
            {
                id: "icon_size_3",
                groupId: "icon_size",
                commandId: "resizeIcon3",
                text: "3x",
                isActive: () => this.hasIconSize("3"),
            },
            {
                id: "icon_size_4",
                groupId: "icon_size",
                commandId: "resizeIcon4",
                text: "4x",
                isActive: () => this.hasIconSize("4"),
            },
            {
                id: "icon_size_5",
                groupId: "icon_size",
                commandId: "resizeIcon5",
                text: "5x",
                isActive: () => this.hasIconSize("5"),
            },
            {
                id: "icon_spin",
                groupId: "icon_spin",
                commandId: "toggleSpinIcon",
                isActive: () => this.hasSpinIcon(),
            },
            {
                id: "icon_replace",
                groupId: "icon_replace",
                commandId: "replaceIcon",
                text: _t("Replace"),
            },
        ],
        color_apply_overrides: this.applyIconColor.bind(this),
    };

    /**
     * @deprecated
     */
    getSelectedIcon() {
        return this.getTargetedIcon();
    }

    getTargetedIcon() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        return targetedNodes.find((node) => node.classList?.contains?.("fa"));
    }

    resizeIcon({ size }) {
        const targetedIcon = this.getTargetedIcon();
        if (!targetedIcon) {
            return;
        }
        for (const classString of targetedIcon.classList) {
            if (classString.match(/^fa-[2-5]x$/)) {
                targetedIcon.classList.remove(classString);
            }
        }
        if (size !== "1") {
            targetedIcon.classList.add(`fa-${size}x`);
        }
        this.dependencies.history.addStep();
    }

    toggleSpinIcon() {
        const selectedIcon = this.getTargetedIcon();
        if (!selectedIcon) {
            return;
        }
        selectedIcon.classList.toggle("fa-spin");
    }

    hasIconSize(size) {
        const selectedIcon = this.getTargetedIcon();
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
        const selectedIcon = this.getTargetedIcon();
        if (!selectedIcon) {
            return;
        }
        return selectedIcon.classList.contains("fa-spin");
    }

    applyIconColor(color, mode) {
        const selectedIcon = this.getTargetedIcon();
        if (!selectedIcon) {
            return;
        }
        this.dependencies.color.colorElement(selectedIcon, color, mode);
        return true;
    }

    openIconDialog() {
        const selectedIcon = this.getSelectedIcon();
        if (!selectedIcon) {
            return;
        }
        this.dependencies.dialog.addDialog(MediaDialog, {
            noVideos: true,
            noImages: true,
            noDocuments: true,
            media: selectedIcon,
            save: (el) => this.onSaveIcon(el, selectedIcon),
        });
    }

    onSaveIcon(icon, prevIcon) {
        for (const attribute of icon.attributes) {
            prevIcon.setAttribute(attribute.nodeName, attribute.nodeValue);
        }
        this.dependencies.history.addStep();
    }
}
