import { Plugin } from "@html_editor/plugin";
import { MEDIA_SELECTOR, isProtected } from "@html_editor/utils/dom_info";
import { closestElement } from "@html_editor/utils/dom_traversal";

export class MediaWebsitePlugin extends Plugin {
    static id = "media_website";
    static dependencies = ["media", "selection"];

    setup() {
        const basicMediaSelector = `${MEDIA_SELECTOR}, img`;
        // (see isImageSupportedForStyle).
        const mediaSelector = basicMediaSelector
            .split(",")
            .map((s) => `${s}:not([data-oe-xpath])`)
            .join(",");
        this.addDomListener(this.editable, "dblclick", (ev) => {
            const targetEl = ev.target;
            if (!targetEl.matches(mediaSelector)) {
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
    }

    onDblClickEditableMedia(mediaEl) {
        const params = { node: mediaEl };
        const sel = this.dependencies.selection.getEditableSelection();

        const editableEl =
            closestElement(params.node || sel.startContainer, ".o_editable") || this.editable;
        this.dependencies.media.openMediaDialog(params, editableEl);
    }
}

function shouldEditableMediaBeEditable(mediaEl) {
    // Some sections of the DOM are contenteditable="false" (for example with
    // the help of the o_not_editable class) but have inner media that should be
    // editable (the fact the container is not is to prevent adding text in
    // between those medias). This case is complex and the solution to support
    // it is not perfect: we mark those media with a class and check that the
    // first non editable ancestor is in fact in an editable parent.
    const parentEl = mediaEl.parentElement;
    const nonEditableAncestorRootEl = parentEl && parentEl.closest("[contenteditable='false']");
    return (
        nonEditableAncestorRootEl &&
        nonEditableAncestorRootEl.parentElement &&
        nonEditableAncestorRootEl.parentElement.isContentEditable
    );
}
