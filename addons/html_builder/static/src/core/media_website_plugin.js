import { Plugin } from "@html_editor/plugin";
import { MEDIA_SELECTOR, isProtected } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { shouldEditableMediaBeEditable } from "@html_builder/utils/utils_css";
import { _t } from "@web/core/l10n/translation";
import { Tooltip } from "@web/core/tooltip/tooltip";

export class MediaWebsitePlugin extends Plugin {
    static id = "media_website";
    static dependencies = ["media", "selection", "builderOptions"];
    static shared = ["replaceMedia"];

    resources = {
        user_commands: [
            {
                id: "websiteVideo",
                title: _t("Video"),
                description: _t("Insert a video"),
                icon: "fa-file-video-o",
                run: this.dependencies.media.openMediaDialog.bind(this, {
                    noVideos: false,
                    noImages: true,
                    noIcons: true,
                    extraTabs: false,
                }),
                isAvailable: isHtmlContentSupported,
            },
        ],
        powerbox_items: [
            {
                categoryId: "media",
                commandId: "websiteVideo",
            },
        ],
        on_replaced_media_handlers: ({ newMediaEl }) =>
            // Activate the new media options.
            this.dependencies.builderOptions.setNextTarget(newMediaEl),
    };

    setup() {
        const basicMediaSelector = `${MEDIA_SELECTOR}, img`;
        // (see isImageSupportedForStyle).
        const mediaSelector = basicMediaSelector
            .split(",")
            .map((s) => `${s}:not([data-oe-xpath])`)
            .join(",");

        this.addDomListener(this.editable, "dblclick", async (ev) => {
            const targetEl = ev.target.closest(mediaSelector);
            if (!targetEl) {
                return;
            }
            if (this.isReplaceableMedia(targetEl)) {
                await this.onDblClickEditableMedia(targetEl);
            }
        });

        this.popover = this.services.popover;
        this.removeCurrentTooltip = () => {};
        this.addDomListener(this.editable, "click", (ev) => {
            const targetEl = ev.target.closest(mediaSelector);
            if (!targetEl) {
                return;
            }
            if (this.isReplaceableMedia(targetEl)) {
                this.openImageTooltip(targetEl);
            }
        });
    }

    destroy() {
        super.destroy();
        this.removeCurrentTooltip();
    }

    /**
     * Checks if the given media can be replaced.
     *
     * @param {HTMLElement} targetEl the media element
     * @returns {Boolean}
     */
    isReplaceableMedia(targetEl) {
        let isEditable =
            // TODO that first check is probably useless/wrong: checking if
            // the media itself has editable content should not be relevant.
            // In fact the content of all media should be marked as non
            // editable anyway.
            targetEl.isContentEditable ||
            // For a media to be editable, the base case is to be in a
            // container whose content is editable.
            (targetEl.parentElement && targetEl.parentElement.isContentEditable);

        if (!isEditable && targetEl.classList.contains("o_editable_media")) {
            isEditable = shouldEditableMediaBeEditable(targetEl);
        }
        if (
            isEditable &&
            !isProtected(this.dependencies.selection.getEditableSelection().anchorNode)
        ) {
            return true;
        }
        return false;
    }

    /**
     * Replaces the double-cliked media element.
     *
     * @param {HTMLElement} mediaEl the media element to replace
     */
    async onDblClickEditableMedia(mediaEl) {
        this.removeCurrentTooltip();
        await this.replaceMedia(mediaEl);
    }

    /**
     * Opens the media dialog to replace the selected media.
     *
     * @param {HTMLElement} mediaEl the media element to replace
     */
    async replaceMedia(mediaEl) {
        const sel = this.dependencies.selection.getEditableSelection();
        const editableEl =
            closestElement(mediaEl || sel.startContainer, ".o_editable") || this.editable;
        await this.dependencies.media.openMediaDialog({ node: mediaEl }, editableEl);
    }

    /**
     * Displays the "double-click" tooltip under the given media element.
     *
     * @param {HTMLElement} mediaEl the media element
     */
    openImageTooltip(mediaEl) {
        // Remove the displayed tooltip if any first.
        this.removeCurrentTooltip();
        this.removeCurrentTooltip = this.popover.add(mediaEl, Tooltip, {
            tooltip: _t("Double-click to edit"),
        });
        setTimeout(this.removeCurrentTooltip, 1500);
    }
}
