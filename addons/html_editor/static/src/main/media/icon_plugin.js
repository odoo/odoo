import { READ, withSequence } from "@html_editor/utils/resource";
import { Plugin } from "../../plugin";
import { _t } from "@web/core/l10n/translation";
import { MediaDialog } from "./media_dialog/media_dialog";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import {
    ICON_SELECTOR,
    ICON_SIZE_CLASS_REGEX,
    getIconType,
    isElement,
    isIconElement,
    isTextNode,
    isZwnbsp,
} from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { proxy } from "@odoo/owl";
import { ImageToolbarDropdown } from "./image_toolbar_dropdown";

const ICON_SIZES = ["1", "2", "3", "4", "5"].map((size) => ({
    id: `icon_size_${size}`,
    name: `${size}x`,
    value: size,
}));

export class IconPlugin extends Plugin {
    static id = "icon";
    static dependencies = ["history", "selection", "color", "dialog"];
    toolbarNamespace = "icon";
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "resizeIcon1",
                description: _t("Resize icon 1x"),
                run: () => this.resizeIcon({ size: "1" }),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "resizeIcon2",
                description: _t("Resize icon 2x"),
                run: () => this.resizeIcon({ size: "2" }),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "resizeIcon3",
                description: _t("Resize icon 3x"),
                run: () => this.resizeIcon({ size: "3" }),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "resizeIcon4",
                description: _t("Resize icon 4x"),
                run: () => this.resizeIcon({ size: "4" }),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "resizeIcon5",
                description: _t("Resize icon 5x"),
                run: () => this.resizeIcon({ size: "5" }),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "toggleSpinIcon",
                description: _t("Toggle icon spin"),
                icon: "progress_activity",
                run: this.toggleSpinIcon.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "replaceIcon",
                description: _t("Replace icon"),
                run: this.openIconDialog.bind(this),
                isAvailable: isHtmlContentSupported,
            },
        ],
        toolbar_namespace_providers: [
            (targetedNodes) => {
                if (!targetedNodes.length) {
                    return;
                }
                const textNodes = targetedNodes.filter(isTextNode);
                if (textNodes.every(isZwnbsp) && targetedNodes.some(isIconElement)) {
                    return this.toolbarNamespace;
                }
            },
        ],
        toolbar_groups: [
            withSequence(2, { id: "icon_size", namespaces: ["icon"] }),
            withSequence(3, { id: "icon_spin", namespaces: ["icon"] }),
            withSequence(3, { id: "icon_replace", namespaces: ["icon"] }),
        ],
        toolbar_items: [
            {
                // A menu showing the current size, as the size of images.
                id: "icon_size",
                groupId: "icon_size",
                description: _t("Resize icon"),
                Component: ImageToolbarDropdown,
                props: {
                    name: "icon_size",
                    icon: "open_in_full",
                    getDisplay: () => this.iconSize,
                    items: ICON_SIZES,
                    isSelected: (item) => this.hasIconSize(item.value),
                    focusEditable: () => this.dependencies.selection.focusEditable(),
                    onSelected: (item) => {
                        this.resizeIcon({ size: item.value });
                        this.updateIconSize();
                    },
                },
                isAvailable: isHtmlContentSupported,
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
                // In words: no icon reads as "replace", as in the builder.
                text: _t("Replace"),
            },
        ],
        on_selectionchange_handlers: withSequence(READ, this.updateIconSize.bind(this)),
        on_history_commit_undone_handlers: this.updateIconSize.bind(this),
        on_history_commit_redone_handlers: this.updateIconSize.bind(this),
        /** Providers */
        selected_background_color_providers: withSequence(
            5,
            this.computeBackgroundColorForIcon.bind(this)
        ),
    };

    setup() {
        this.iconSize = proxy({ displayName: "1x" });
    }

    updateIconSize() {
        const item = ICON_SIZES.find((size) => this.hasIconSize(size.value));
        this.iconSize.displayName = item ? item.name : "1x";
    }

    getTargetedIcon() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        return targetedNodes.find((node) => isElement(node) && node.matches(ICON_SELECTOR));
    }

    resizeIcon({ size }) {
        const targetedIcon = this.getTargetedIcon();
        if (!targetedIcon) {
            return;
        }
        for (const classString of [...targetedIcon.classList]) {
            if (ICON_SIZE_CLASS_REGEX.test(classString)) {
                targetedIcon.classList.remove(classString);
            }
        }
        const iconType = getIconType(targetedIcon);
        if (size !== "1" && iconType) {
            targetedIcon.classList.add(`${iconType}-${size}x`);
        }
        this.dependencies.history.commit();
    }

    toggleSpinIcon() {
        const selectedIcon = this.getTargetedIcon();
        if (!selectedIcon) {
            return;
        }
        selectedIcon.classList.toggle("oi-spin");
        this.dependencies.history.commit();
    }

    hasIconSize(size) {
        const selectedIcon = this.getTargetedIcon();
        if (!selectedIcon) {
            return false;
        }
        if (size === "1") {
            return ![...selectedIcon.classList].some((classString) =>
                ICON_SIZE_CLASS_REGEX.test(classString)
            );
        }
        const iconType = getIconType(selectedIcon);
        return !!(iconType && selectedIcon.classList.contains(`${iconType}-${size}x`));
    }

    hasSpinIcon() {
        const selectedIcon = this.getTargetedIcon();
        if (!selectedIcon) {
            return;
        }
        return (
            selectedIcon.classList.contains("oi-spin") || selectedIcon.classList.contains("fa-spin")
        );
    }

    openIconDialog() {
        const selectedIcon = this.getTargetedIcon();
        if (!selectedIcon) {
            return;
        }
        this.dependencies.dialog.addDialog(MediaDialog, {
            visibleTabs: ["ICONS"],
            media: selectedIcon,
            save: (el) => this.onSaveIcon(el, selectedIcon),
            document: this.document,
        });
    }

    onSaveIcon(icon, prevIcon) {
        for (const attribute of icon.attributes) {
            prevIcon.setAttribute(attribute.nodeName, attribute.nodeValue);
        }
        this.dependencies.history.commit();
    }

    computeBackgroundColorForIcon() {
        const nodes = this.dependencies.selection
            .getTargetedNodes()
            .filter((node) => node.classList?.contains("oi"));
        if (nodes.length === 0) {
            return;
        }
        const el = closestElement(nodes[0], "font");
        if (!el) {
            return;
        }
        return this.dependencies.color.getElementColors(el).backgroundColor;
    }
}
