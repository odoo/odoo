/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            componentName
        [Field/model]
            Dialog
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isRequired]
            true
        [Field/compute]
            {if}
                @record
                .{Dialog/attachmentViewer}
            .{then}
                AttachmentViewerComponent
            .{elif}
                @record
                .{Dialog/attachmentDeleteConfirmView}
            .{then}
                AttachmentDeleteConfirmComponent
            .{elif}
                @record
                .{Dialog/deleteMessageConfirmView}
            .{then}
                DeleteMessageConfirmComponent
            .{elif}
                @record
                .{Dialog/followerSubtypeList}
            .{then}
                FollowerSubtypeListComponent
            .{else}
                {Record/empty}
`;
