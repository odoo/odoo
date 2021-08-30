/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles the click on delete attachment and open the confirm dialog.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentCard/onClickUnlink
        [Action/params]
            ev
                [type]
                    web.MouseEvent
            record
                [type]
                    AttachmentCard
        [Action/behavior]
            {Dev/comment}
                prevents from opening viewer
            {web.Event/stopPropagation}
                @ev
            {if}
                @record
                .{AttachmentCard/attachmentList}
                .{AttachmentList/composerViewOwner}
            .{then}
                {Component/trigger}
                    [0]
                        @record
                        .{AttachmentCard/component}
                    [1]
                        o-attachment-removed
                    [2]
                        [attachment]
                            @record
                            .{AttachmentCard/attachment}
                {Attachment/remove}
                    @record
                    .{AttachmentCard/attachment}
            .{else}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [AttachmentCard/attachmentDeleteConfirmDialog]
                            {Record/insert}
                                [Record/models]
                                    Dialog
`;
