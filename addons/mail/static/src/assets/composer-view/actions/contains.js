/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Returns whether the given html element is inside this composer view,
        including whether it's inside the emoji popover when active.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ComposerView/contains
        [Action/params]
            element
                [type]
                    web.Element
            record
                [type]
                    ComposerView
        [Action/behavior]
            {Dev/comment}
                emoji popover is outside but should be considered inside
            {if}
                @record
                .{ComposerView/emojisPopoverView}
                .{&}
                    {PopoverView/contains}
                        [0]
                            @record
                            .{ComposerView/emojisPopoverView}
                        [1]
                            @element
            .{then}
                true
            .{else}
                @record
                .{ComposerView/component}
                .{&}
                    @record
                    .{ComposerView/component}
                    .{ComposerViewComponent/root}
                .{&}
                    @record
                    .{ComposerView/component}
                    .{ComposerViewComponent/root}
                    .{web.Element/contains}
                        @element
`;
