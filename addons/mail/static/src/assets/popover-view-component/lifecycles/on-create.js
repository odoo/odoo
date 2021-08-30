/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onCreate
        [Lifecycle/model]
            PopoverViewComponent
        [Lifecycle/behavior]
            {PositionHook/usePosition}
                [0]
                    {if}
                        @record
                        .{PopoverViewComponent/popoverView}
                        .{isFalsy}
                    .{then}
                        {break}
                    {if}
                        @record
                        .{PopoverViewComponent/popoverView}
                        .{PopoverView/anchorRef}
                        .{isFalsy}
                    .{then}
                        {break}
                    @record
                    .{PopoverViewComponent/popoverView}
                    .{PopoverView/anchorRef}
                [1]
                    root
                [2]
                    [margin]
                        16
                    [position]
                        @record
                        .{PopoverViewComponent/popoverView}
                        .{PopoverView/position}
`;
