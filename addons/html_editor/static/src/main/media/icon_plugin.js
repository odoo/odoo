import { withSequence } from "@html_editor/utils/resource";
import { Plugin, shared } from "../../plugin";
import { signal } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { uniqueId } from "@web/core/utils/functions";
import { IconPicker } from "./icon_picker/icon_picker";
import {
    ICON_SELECTOR,
    ICON_SIZE_CLASS_REGEX,
    getIconType,
    iconClasses,
    isElement,
    isIconElement,
} from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";

/**
 * @typedef {((params: {
 *      iconEl: HTMLElement,
 *      file: File,
 *      sourceEl: HTMLElement,
 * }) => Promise<void>)[]} replace_icon_by_image_handlers
 * Replace the given icon by an image uploaded from the given file, taking
 * over the classes and style of `sourceEl`: a copy of the icon without what
 * only applies to icons. Offered in the icon picker when there is one.
 */
import { rightPos } from "@html_editor/utils/position";

export class IconPlugin extends Plugin {
    static id = "icon";
    static dependencies = ["history", "selection", "color", "dom", "overlay"];
    static shared = shared(["openIconPicker", "pickIcon"]);
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "insertIcon",
                title: _t("Icon"),
                description: _t("Insert an icon"),
                icon: "add_reaction",
                run: () => this.openIconPicker(),
                isAvailable: (selection) =>
                    this.dependencies.dom.supportsHtmlContent(selection) &&
                    !closestElement(selection.anchorNode, "label"),
            },
            {
                id: "resizeIcon1",
                description: _t("Resize icon 1x"),
                run: () => this.resizeIcon({ size: "1" }),
            },
            {
                id: "resizeIcon2",
                description: _t("Resize icon 2x"),
                run: () => this.resizeIcon({ size: "2" }),
            },
            {
                id: "resizeIcon3",
                description: _t("Resize icon 3x"),
                run: () => this.resizeIcon({ size: "3" }),
            },
            {
                id: "resizeIcon4",
                description: _t("Resize icon 4x"),
                run: () => this.resizeIcon({ size: "4" }),
            },
            {
                id: "resizeIcon5",
                description: _t("Resize icon 5x"),
                run: () => this.resizeIcon({ size: "5" }),
            },
            {
                id: "toggleSpinIcon",
                description: _t("Toggle icon spin"),
                icon: "play_arrow",
                run: this.toggleSpinIcon.bind(this),
            },
            {
                id: "replaceIcon",
                description: _t("Replace icon"),
                run: this.openReplaceIconPicker.bind(this),
            },
        ],
        // Next to the media command, in the category of the media plugin, and
        // only where that command is available.
        ...(this.config.allowImage && {
            powerbox_items: {
                categoryId: "media",
                commandId: "insertIcon",
                keywords: [_t("Icons"), _t("Pictogram")],
            },
        }),
        properties: [{ predicate: isIconElement, toolbar: "icon" }],
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
                opensUi: true,
                popup: "dialog",
                popupId: () => this.iconPickerId(),
                icon: "image",
            },
        ],
        /** Providers */
        selected_background_color_providers: withSequence(
            5,
            this.computeBackgroundColorForIcon.bind(this)
        ),
    };

    setup() {
        /** The id of the open icon picker, referenced by the Replace button. */
        this.iconPickerId = signal(null);
        this.iconPickerOverlay = this.dependencies.overlay.createOverlay(
            IconPicker,
            { hasAutofocus: true, className: "popover" },
            { onRemove: this.onIconPickerRemoved.bind(this) }
        );
        /** Called when the open icon picker is closed, whatever the reason. */
        this.onIconPickerClose = null;
        this.addDomListener(this.editable, "dblclick", (ev) => {
            const iconEl = closestElement(ev.target, isIconElement);
            if (iconEl && this.isReplaceableOnDblClick(iconEl)) {
                this.openIconPicker({ iconEl });
            }
        });
    }

    /**
     * @param {HTMLElement} iconEl
     * @returns {boolean} whether double-clicking the icon opens the icon picker
     */
    isReplaceableOnDblClick(iconEl) {
        return !!iconEl.parentElement?.isContentEditable;
    }

    onIconPickerRemoved() {
        const onClose = this.onIconPickerClose;
        this.onIconPickerClose = null;
        this.iconPickerId.set(null);
        onClose?.();
    }

    /**
     * Opens the icon picker, to insert an icon at the selection or to replace
     * the given one.
     *
     * @param {Object} [params]
     * @param {HTMLElement} [params.iconEl] the icon to replace, highlighted in
     *  the picker, which is positioned next to it
     * @param {HTMLElement} [params.target] the element to position the picker
     *  next to, instead of the icon or the selection
     * @param {string} [params.label] the accessible name of the picker, which
     *  should be the one of the button that opens it
     * @param {(icon: { name: string, filled: boolean }) => void} [params.onSelect]
     *  called with the picked icon instead of inserting or replacing one
     * @param {() => void} [params.onClose] called when the picker is closed,
     *  after `onSelect` if an icon was picked
     */
    openIconPicker({ iconEl, target, label, onSelect, onClose } = {}) {
        // A single picker at a time: the open one, if any, is closed first.
        this.iconPickerOverlay.close();
        const id = uniqueId("o-we-icon-picker-");
        this.iconPickerId.set(id);
        this.onIconPickerClose = onClose;
        this.iconPickerOverlay.open({
            target: target || iconEl,
            props: {
                id,
                label: label || (iconEl ? _t("Replace icon") : _t("Insert an icon")),
                document: this.document,
                onUploadImage:
                    iconEl && !onSelect && this.getResource("replace_icon_by_image_handlers").length
                        ? (file) => this.replaceIconByImage(iconEl, file)
                        : undefined,
                currentIcon: iconEl?.dataset.icon
                    ? {
                          name: iconEl.dataset.icon,
                          filled: iconEl.classList.contains("oi-filled"),
                      }
                    : undefined,
                close: () => {
                    this.iconPickerOverlay.close();
                    this.dependencies.selection.focusEditable();
                },
                onSelect: (icon) => {
                    if (onSelect) {
                        onSelect(icon);
                    } else if (iconEl) {
                        this.replaceIcon(iconEl, icon);
                    } else {
                        this.insertIcon(icon);
                    }
                },
            },
        });
    }

    /**
     * Lets the user pick an icon from the icon picker, e.g. for an option.
     *
     * @param {Object} [params]
     * @param {HTMLElement} [params.target] the element to position the picker
     *  next to, the selection by default
     * @param {HTMLElement} [params.iconEl] the current icon, highlighted in the
     *  picker
     * @param {string} [params.label] the accessible name of the picker
     * @returns {Promise<HTMLElement | undefined>} a new element of the picked
     *  icon, or `undefined` if the picker was closed without picking one
     */
    pickIcon({ target, iconEl, label = _t("Select an icon") } = {}) {
        return new Promise((resolve) => {
            this.openIconPicker({
                target,
                iconEl,
                label,
                onSelect: (icon) => resolve(this.createIconElement(icon)),
                onClose: () => resolve(),
            });
        });
    }

    /**
     * @param {{ name: string, filled: boolean }} icon
     * @returns {HTMLElement}
     */
    createIconElement({ name, filled }) {
        const iconEl = this.document.createElement("span");
        iconEl.classList.add("oi");
        iconEl.classList.toggle("oi-filled", filled);
        iconEl.dataset.icon = name;
        return iconEl;
    }

    /**
     * @param {{ name: string, filled: boolean }} icon
     */
    insertIcon(icon) {
        const iconEl = this.createIconElement(icon);
        this.dependencies.dom.insert(iconEl);
        const [anchorNode, anchorOffset] = rightPos(iconEl);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        this.dependencies.history.commit();
    }

    /**
     * @param {HTMLElement} iconEl
     * @param {File} file
     */
    async replaceIconByImage(iconEl, file) {
        await this.triggerAsync("replace_icon_by_image_handlers", {
            iconEl,
            file,
            sourceEl: this.getImageSourceElement(iconEl),
        });
    }

    /**
     * @param {HTMLElement} iconEl
     * @returns {HTMLElement} a copy of the icon without the classes and the
     *  style that only apply to icons (glyph, fill, size, spin, colors), so
     *  that an image replacing it keeps the others (e.g. shape, alignment)
     */
    getImageSourceElement(iconEl) {
        const sourceEl = iconEl.cloneNode(false);
        const iconOnlyClasses = [...sourceEl.classList].filter(
            (cls) => iconClasses.includes(cls) || /^(oi|fa|text|bg)-/.test(cls)
        );
        sourceEl.classList.remove(...iconOnlyClasses);
        sourceEl.style.removeProperty("color");
        sourceEl.style.removeProperty("background-color");
        return sourceEl;
    }

    openReplaceIconPicker() {
        const iconEl = this.getTargetedIcon();
        if (iconEl) {
            this.openIconPicker({ iconEl });
        }
    }

    /**
     * Changes the glyph of an icon, keeping its tag and its other classes
     * (size, color, spin...), except those of a legacy FontAwesome icon.
     *
     * @param {HTMLElement} iconEl
     * @param {{ name: string, filled: boolean }} icon
     */
    replaceIcon(iconEl, { name, filled }) {
        const fontAwesomeClasses = [...iconEl.classList].filter(
            (cls) => ["fa", "fab", "fad", "far"].includes(cls) || cls.startsWith("fa-")
        );
        iconEl.classList.remove(...fontAwesomeClasses);
        iconEl.classList.add("oi");
        iconEl.classList.toggle("oi-filled", filled);
        iconEl.dataset.icon = name;
        this.dependencies.history.commit();
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
