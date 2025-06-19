import { Plugin } from "@html_editor/plugin";
import { MEDIA_SELECTOR, isProtected } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { shouldEditableMediaBeEditable } from "@html_builder/utils/utils_css";
import { _t } from "@web/core/l10n/translation";
import { Tooltip } from "@web/core/tooltip/tooltip";

export class MediaWebsitePlugin extends Plugin {
    static id = "media_website";
    static dependencies = ["media", "selection", "builderOptions"];
    static shared = ["replaceMedia"];

    resources = {
        on_replaced_media_handlers: ({ newMediaEl }) =>
            // Activate the new media options.
            this.dependencies.builderOptions.setNextTarget(newMediaEl),
        on_snippet_dropped_handlers: this.onSnippetDropped.bind(this),
    };

    setup() {
        const basicMediaSelector = `${MEDIA_SELECTOR}, img`;

        this.addDomListener(this.editable, "dblclick", async (ev) => {
            const targetEl = ev.target.closest(basicMediaSelector);
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
            const targetEl = ev.target.closest(basicMediaSelector);
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
        // For a media to be editable, the base case is to be in a
        // container whose content is editable.
        let isEditable = targetEl.parentElement?.isContentEditable;

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

    async onSnippetDropped({ snippetEl }) {
        if (!snippetEl.matches(".media_iframe_video")) {
            return;
        }
        let isVideoSelected = false;
        await new Promise((resolve) => {
            const onClose = this.dependencies.media.openMediaDialog({
                activeTab: "VIDEOS",
                save: async (selectedVideoEl) => {
                    isVideoSelected = true;
                    snippetEl.insertAdjacentElement("afterend", selectedVideoEl);
                    snippetEl.remove();
                },
            });
            onClose.then(() => {
                resolve();
            });
        });
        return !isVideoSelected;
    }
}
