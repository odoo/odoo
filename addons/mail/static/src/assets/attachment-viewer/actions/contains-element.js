/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given html element is inside this attachment viewer.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentViewer/containsElement
        [Action/params]
            element
                [type]
                    web.Element
            record
                [type]
                    AttachmentViewer
        [Action/behavior]
            @record
            .{AttachmentViewer/component}
            .{&}
                @record
                .{AttachmentViewer/component}
                .{AttachmentViewerComponent/root}
                .{web.Element/contains}
                    @element
`;
