/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given html element is inside this delete message confirm view.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DeleteMessageConfirmView/containsElement
        [Action/params]
            element
                [type]
                    web.Element
            record
                [type]
                    DeleteMessageConfirmView
        [Action/returns]
            Boolean
        [Action/behavior]
            @record
            .{DeleteMessageConfirmView/component}
            .{&}
                {web.Element/contains}
                    [0]
                        @record
                        .{DeleteMessageConfirmView/component}
                        .{DeleteMessageConfirmComponent/root}
                    [1]
                        @element
`;
