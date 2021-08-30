/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Closes the popover when clicking outside, if appropriate.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            PopoverView/_onClickCaptureGlobal
        [Action/params]
            record
                [type]
                    PopoverView
            ev
                [type]
                    web.MouseEvent
        [Action/behavior]
            {if}
                @record
                .{PopoverView/component}
                .{isFalsy}
            .{then}
                {break}
            {if}
                @record
                .{PopoverView/anchorRef}
                .{&}
                    {web.Element/contains}
                        [0]
                            @record
                            .{PopoverView/anchorRef}
                        [1]
                            @ev
                            .{web.Event/target}
            .{then}
                {break}
            {if}
                {web.Element/contains}
                    [0]
                        @record
                        .{PopoverView/component}
                    [1]
                        @ev
                        .{web.Event/target}
            .{then}
                {break}
            {Record/delete}
                @record
`;
