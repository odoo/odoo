import {canPreview, showPreview} from "../utils.esm";
import {AttachmentList} from "@mail/core/common/attachment_list";
import {patch} from "@web/core/utils/patch";

patch(AttachmentList.prototype, {
    _onPreviewAttachment(attachment) {
        // eslint-disable-next-line no-undef
        var $target = $(event.currentTarget);
        var split_screen = $target.attr("data-target") !== "new";
        showPreview(
            attachment.id,
            attachment.defaultSource,
            attachment.extension,
            attachment.filename,
            split_screen,
            this.previewableAttachments
        );
    },

    _canPreviewAttachment(attachment) {
        return canPreview(attachment.extension);
    },
});
