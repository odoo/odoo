/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given html element is inside this attachment delete confirm view.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            AttachmentDeleteConfirmView/containsElement
        [Action/params]
            element
                [type]
                    web.Element
            record
                [type]
                    AttachmentDeleteConfirmView
        [Action/returns]
            Boolean
        [Action/behavior]
            @record
            .{AttachmentDeleteConfirmView/component}
            .{&}
                {web.Element/contains}
                    [0]
                        @record
                        .{AttachmentDeleteConfirmView/component}
                        .{AttachmentDeleteConfirmComponent/root}
                    [1]
                        @element
`;
