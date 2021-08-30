/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentDeleteConfirmView/onClickOk
        [Action/params]
            record
                [type]
                    AttachmentDeleteConfirmView
        [Action/behavior]
            {Attachment/remove}
                @record
                .{AttachmentDeleteConfirmView/attachment}
            {if}
                @record
                .{AttachmentDeleteConfirmView/chatter}
                .{&}
                    @record
                    .{AttachmentDeleteConfirmView/chatter}
                    .{Chatter/component}
            .{then}
                {Component/trigger}
                    [0]
                        @record
                        .{AttachmentDeleteConfirmView/chatter}
                        .{Chatter/component}
                    [1]
                        o-attachments-changed
`;
