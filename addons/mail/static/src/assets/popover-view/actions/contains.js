/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given html element is inside the component
        of this popover view.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            PopoverView/contains
        [Action/params]
            record
                [type]
                    PopoverView
            element
                [type]
                    web.Element
        [Action/behavior]
            @record
            .{PopoverView/component}
            .{&}
                @record
                .{PopoverView/component}
                .{PopoverViewComponent/root}
                .{web.Element/contains}
                    @element
`;
