/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isCloseable
        [Field/model]
            Dialog
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            true
        [Field/compute]
            {if}
                @record
                .{Dialog/attachmentViewer}
            .{then}
                {Dev/comment}
                    Prevent closing the dialog when clicking on the mask when the user is
                    currently dragging the image.
                @record
                .{Dialog/attachmentViewer}
                .{AttachmentViewer/isDragging}
                .{isFalsy}
            .{else}
                true
`;
