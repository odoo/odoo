import { withSequence } from "@html_editor/utils/resource";
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
} from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";

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
                icon: "fa-play",
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
        region_properties: { is: isIconElement, toolbar: this.toolbarNamespace },
        toolbar_groups: [
            withSequence(2, { id: "icon_size", namespaces: ["icon"] }),
            withSequence(3, { id: "icon_spin", namespaces: ["icon"] }),
            withSequence(3, { id: "icon_replace", namespaces: ["icon"] }),
        ],
        toolbar_items: [
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
                icon: "fa-file-image-o",
            },
        ],
        click_overrides: this.onClickIcon.bind(this),
        would_feff_be_legit_predicates: (node) => {
            if (
                (node.previousSibling && isIconElement(closestElement(node.previousSibling))) ||
                (node.nextSibling && isIconElement(closestElement(node.nextSibling)))
            ) {
                return true;
            }
        },
        /** Providers */
        selected_background_color_providers: withSequence(
            5,
            this.computeBackgroundColorForIcon.bind(this)
        ),
    };

    onClickIcon(ev) {
        const node = ev.target;
        if (
            isIconElement(closestElement(node)) &&
            !this.dependencies.selection.isNodeEditable(node)
        ) {
            // We select around an icon inside non editable.
            // This might, in case icon inside link, show the link
            // popover to be able to open link.
            this.dependencies.selection.selectElement(node);
        }
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
        selectedIcon.classList.toggle("fa-spin");
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
        return selectedIcon.classList.contains("fa-spin");
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
            .filter((node) => node.classList?.contains("fa"));
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
