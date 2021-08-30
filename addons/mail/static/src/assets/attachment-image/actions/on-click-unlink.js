/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles the click on delete attachment and open the confirm dialog.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentImage/onClickUnlink
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    AttachmentImage
        [Action/behavior]
            {Dev/comment}
                prevents from opening viewer
            {web.Event/stopPropagation}
                @ev
            {if}
                @record
                .{AttachmentImage/attachment}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{AttachmentImage/attachmentList}
                .{AttachmentList/composerViewOwner}
            .{then}
                {Component/trigger}
                    [0]
                        o-attachment-removed
                    [1]
                        [attachment]
                            @record
                            .{AttachmentImage/attachment}
                {Attachment/remove}
                    @record
                    .{AttachmentImage/attachment}
            .{else}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [AttachmentImage/attachmentDeleteConfirmDialog]
                            {Record/insert}
                                [Record/models]
                                    Dialog
`;
