/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Handles mouseenter on the "thread description" of this top bar.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onMouseEnterTopBarThreadDescription
        [Action/params]
            ev
                [type]
                    MouseEvent
            record
                [type]
                    ThreadViewTopbar
        [Action/behavior]
            {if}
                @record
                .{ThreadViewTopbar/thread}
                .{isFalsy}
                .{|}
                    @record
                    .{ThreadViewTopbar/thread}
                    .{Thread/isChannelDescriptionChangeable}
                    .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/isMouseOverThreadDescription]
                        true
`;
