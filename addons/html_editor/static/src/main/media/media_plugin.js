import { Plugin } from "@html_editor/plugin";
import {
    ICON_SELECTOR,
    MEDIA_SELECTOR,
    EDITABLE_MEDIA_CLASS,
    isIconElement,
    isMediaElement,
    isProtected,
    isProtecting,
    paragraphRelatedElementsSelector,
    isContentEditable,
} from "@html_editor/utils/dom_info";
import { _t } from "@web/core/l10n/translation";
import { MediaDialog, TABS } from "./media_dialog/media_dialog";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { boundariesOut, rightPos } from "@html_editor/utils/position";
import { withSequence } from "@html_editor/utils/resource";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { fuzzyLookup } from "@web/core/utils/search";
import { FORMATTABLE_TAGS } from "@html_editor/utils/formatting";

/**
 * @typedef { Object } MediaShared
 * @property { MediaPlugin['openMediaDialog'] } openMediaDialog
 */

/**
 * @typedef {((mediaEl: HTMLElement) => void)[]} after_save_media_dialog_handlers
 * @typedef {((arg: { newMediaEl: HTMLElement }) => void)[]} on_added_media_handlers
 * @typedef {((elements: HTMLElement[], params: { node: Node }) => Promise<void>)[]} on_media_dialog_saved_handlers
 * @typedef {((arg: { newMediaEl: HTMLElement }) => void)[]} on_replaced_media_handlers
 * @typedef {((args: {imageEl: HTMLElement}) => void)[]} on_image_saved_handlers
 *
 * @typedef {{
 *      id: "DOCUMENTS" | "ICONS" | "IMAGES" | "VIDEOS";
 *      title: import("plugins").TranslatedString;
 *      Component: import("@odoo/owl").Component;
 *      sequence: number;
 *  }[]} media_dialog_extra_tabs
 */

export class MediaPlugin extends Plugin {
    static id = "media";
    static dependencies = ["selection", "history", "dom", "dialog"];
    static shared = ["openMediaDialog"];
    static defaultConfig = {
        allowImage: true,
        allowMediaDocuments: true,
    };
    /** @type {import("plugins").EditorResources} */
    resources = {
        user_commands: [
            {
                id: "replaceImage",
                description: _t("Replace media"),
                icon: "fa-exchange",
                run: this.replaceImage.bind(this),
                isAvailable: isHtmlContentSupported,
            },
            {
                id: "insertMedia",
                title: _t("Media"),
                description: this.config.allowVideo
                    ? _t("Insert image, icon or video")
                    : _t("Insert image or icon"),
                icon: "fa-file-image-o",
                run: (params, context = {}) =>
                    this.openMediaDialog({
                        activeTab: this.getActiveDialogTab(context.searchTerm),
                    }),
                isAvailable: isHtmlContentSupported,
            },
        ],
        toolbar_groups: withSequence(31, { id: "replace_image", namespaces: ["image"] }),
        toolbar_items: [
            {
                id: "replace_image",
                groupId: "replace_image",
                commandId: "replaceImage",
            },
        ],
        powerbox_categories: withSequence(40, { id: "media", name: _t("Media") }),
        ...(this.config.allowImage && {
            powerbox_items: this.getInsertMediaPowerboxItem(),
        }),
        power_buttons: withSequence(1, { commandId: "insertMedia" }),
        closest_savable_providers: withSequence(20, (el) => this.editable),

        /** Handlers */
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
        normalize_handlers: this.normalizeMedia.bind(this),
        selectionchange_handlers: this.selectAroundIcon.bind(this),

        unsplittable_node_predicates: isIconElement, // avoid merge
        is_node_editable_predicates: this.isEditableMediaElement.bind(this),
        clipboard_content_processors: this.clean.bind(this),
        clipboard_text_processors: (text) => text.replace(/\u200B/g, ""),
        functional_empty_node_predicates: isMediaElement,

        selectors_for_feff_providers: () =>
            `:is(${paragraphRelatedElementsSelector}, ${FORMATTABLE_TAGS.join(
                ", "
            )}, A, LI) > :is(${ICON_SELECTOR})`,
    };

    setup() {
        this.availableTabs = [
            ...Object.values(TABS),
            ...this.getResource("media_dialog_extra_tabs"),
        ];
    }

    getInsertMediaPowerboxItem() {
        const self = this;
        return {
            categoryId: "media",
            commandId: "insertMedia",
            // Evaluation is deferred because this.availableTabs is only ready after setup.
            get keywords() {
                return self.availableTabs.map((tab) => tab.title);
            },
        };
    }

    getRecordInfo(editableEl = null) {
        return this.config.getRecordInfo ? this.config.getRecordInfo(editableEl) : {};
    }

    isEditableMediaElement(node) {
        if (
            (isMediaElement(node) || node.nodeName === "IMG") &&
            (node.classList.contains(EDITABLE_MEDIA_CLASS) || isContentEditable(node))
        ) {
            return true;
        }
    }

    replaceImage() {
        const targetedNodes = this.dependencies.selection.getTargetedNodes();
        const node = targetedNodes.find((node) => node.tagName === "IMG");
        if (node) {
            this.openMediaDialog({ node });
            this.dependencies.history.addStep();
        }
    }

    normalizeMedia(node) {
        const mediaElements = [...node.querySelectorAll(MEDIA_SELECTOR)];
        if (node.matches(MEDIA_SELECTOR)) {
            mediaElements.push(node);
        }
        for (const el of mediaElements) {
            if (isProtected(el) || isProtecting(el)) {
                continue;
            }
            el.setAttribute(
                "contenteditable",
                el.hasAttribute("contenteditable") ? el.getAttribute("contenteditable") : "false"
            );
            // Do not update the text if it's already OK to avoid recording a
            // mutation on Firefox. (Chrome filters them out.)
            if (isIconElement(el) && el.textContent !== "\u200B") {
                el.textContent = "\u200B";
            }
        }
    }

    clean(root) {
        for (const el of root.querySelectorAll(MEDIA_SELECTOR)) {
            if (isIconElement(el)) {
                el.textContent = "";
            }
        }
    }

    cleanForSave(root) {
        for (const el of root.querySelectorAll(MEDIA_SELECTOR)) {
            if (isIconElement(el)) {
                el.textContent = "";
            }
            el.removeAttribute("contenteditable");
        }
    }

    async onSaveMediaDialog(element, { node }) {
        if (!element) {
            // @todo @phoenix to remove
            throw new Error("Element is required: onSaveMediaDialog");
            // return;
        }
        if (node) {
            const changedIcon = isIconElement(node) && isIconElement(element);
            if (changedIcon) {
                // Preserve tag name when changing an icon and not recreate the
                // editors unnecessarily.
                for (const attribute of element.attributes) {
                    node.setAttribute(attribute.nodeName, attribute.nodeValue);
                }
                element = node;
            } else {
                node.replaceWith(element);
            }
            this.dispatchTo("on_replaced_media_handlers", { newMediaEl: element });
        } else {
            this.dependencies.dom.insert(element);
            this.dispatchTo("on_added_media_handlers", { newMediaEl: element });
        }
        // Collapse selection after the inserted/replaced element.
        const [anchorNode, anchorOffset] = rightPos(element);
        this.dependencies.selection.setSelection({ anchorNode, anchorOffset });
        this.dispatchTo("after_save_media_dialog_handlers", element);
        this.dependencies.history.addStep();
    }

    openMediaDialog(params = {}, editableEl = null) {
        const oldSave =
            params.save || ((element) => this.onSaveMediaDialog(element, { node: params.node }));
        params.save = async (...args) => {
            const selection = args[0];
            const elements = selection
                ? selection[Symbol.iterator]
                    ? selection
                    : [selection]
                : [];
            for (const onMediaDialogSaved of this.getResource("on_media_dialog_saved_handlers")) {
                await onMediaDialogSaved(elements, { node: params.node });
            }
            return oldSave(...args);
        };
        const { resModel, resId, field, type } = this.getRecordInfo(editableEl);
        const mediaDialogClosedPromise = this.dependencies.dialog.addDialog(MediaDialog, {
            resModel,
            resId,
            useMediaLibrary: !!(
                field &&
                ((resModel === "ir.ui.view" && field === "arch") || type === "html")
            ), // @todo @phoenix: should be removed and moved to config.mediaModalParams
            media: params.node,
            onAttachmentChange: this.config.onAttachmentChange || (() => {}),
            noImages: !this.config.allowImage,
            extraTabs: this.getResource("media_dialog_extra_tabs"),
            ...this.config.mediaModalParams,
            ...params,
        });
        return mediaDialogClosedPromise;
    }

    /**
     * @param {import("@html_editor/core/selection_plugin").SelectionData} param0
     */
    selectAroundIcon({ editableSelection }) {
        if (!editableSelection.isCollapsed) {
            return;
        }
        const iconEl = closestElement(editableSelection.anchorNode, isIconElement);
        if (!iconEl) {
            return;
        }
        const [anchorNode, anchorOffset, focusNode, focusOffset] = boundariesOut(iconEl);
        const iconOuterBoundaries = { anchorNode, anchorOffset, focusNode, focusOffset };
        this.dependencies.selection.setSelection(iconOuterBoundaries);
    }

    /**
     * @param {string} searchTerm
     * @returns {string|undefined}
     */
    getActiveDialogTab(searchTerm) {
        if (!searchTerm) {
            return undefined;
        }
        const matchedTabs = fuzzyLookup(searchTerm, this.availableTabs, (tab) => tab.title);
        if (!matchedTabs.length) {
            return undefined;
        }
        return matchedTabs[0].id;
    }
}
