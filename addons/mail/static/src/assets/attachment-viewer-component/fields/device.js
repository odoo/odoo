/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            device
        [Field/model]
            AttachmentViewerComponent
        [Field/type]
            one
        [Field/target]
            Device
        [Field/default]
            {Env/device}
        [Field/observe]
            {Record/insert}
                [Record/models]
                    FieldObserver
                [FieldObserver/event]
                    click
                [FieldObserver/callback]
                    {if}
                        @record
                        .{AttachmentViewerComponent/attachmentViewer}
                        .{AttachmentViewer/isDragging}
                        .{isFalsy}
                    .{then}
                        {break}
                    {web.Event/stopPropagation}
                        @ev
                    {AttachmentViewerComponent/_stopDragging}
                        @record
`;