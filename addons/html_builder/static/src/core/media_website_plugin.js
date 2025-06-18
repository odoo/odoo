import { Plugin } from "@html_editor/plugin";
import { MEDIA_SELECTOR, isProtected } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { shouldEditableMediaBeEditable } from "@html_builder/utils/utils_css";
import { _t } from "@web/core/l10n/translation";
import { isHtmlContentSupported } from "@html_editor/core/selection_plugin";
import { Tooltip } from "@web/core/tooltip/tooltip";


export class MediaWebsitePlugin extends Plugin {
    static id = "media_website";
    static dependencies = ["media", "selection"];

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
    };

    setup() {
        const basicMediaSelector = `${MEDIA_SELECTOR}, img`;
        // (see isImageSupportedForStyle).
        const mediaSelector = basicMediaSelector
            .split(",")
            .map((s) => `${s}:not([data-oe-xpath])`)
            .join(",");
        this.addDomListener(this.editable, "dblclick", (ev) => {
            const targetEl = ev.target.closest(mediaSelector);
            if (!targetEl) {
                return;
            }
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
                this.onDblClickEditableMedia(targetEl);
            }
        });

        this.popover = this.services.popover;
        this.tooltipTimeouts = [];
        this.removeCurrentTooltip = () => {};

        this.addDomListener(this.editable, "click", (ev) => {
            const targetEl = ev.target.closest(mediaSelector);
            if (!targetEl) {
                return;
            }
            let isEditable = (targetEl.parentElement && targetEl.parentElement.isContentEditable);

            if (!isEditable && targetEl.classList.contains("o_editable_media")) {
                isEditable = shouldEditableMediaBeEditable(targetEl);
            }
            if (
                isEditable &&
                !isProtected(this.dependencies.selection.getEditableSelection().anchorNode)
            ) {
                this.openImageTooltip(targetEl);
            }
        });
    }

    onDblClickEditableMedia(mediaEl) {
        this.removeCurrentTooltip();

        const params = { node: mediaEl };
        const sel = this.dependencies.selection.getEditableSelection();

        const editableEl =
            closestElement(params.node || sel.startContainer, ".o_editable") || this.editable;
        this.dependencies.media.openMediaDialog(params, editableEl);
    }

    openImageTooltip(mediaEl) {
        //delete last tooltip if it's still displayed
        this.removeCurrentTooltip();
        
        const removeTooltip = this.popover.add(mediaEl, Tooltip, { tooltip: _t('Double-click to edit')});
        setTimeout(() => { removeTooltip() }, 1500);
        this.removeCurrentTooltip = removeTooltip.bind(this);
    }

    destroy() {
        super.destroy();
        this.removeCurrentTooltip();
    }
}
