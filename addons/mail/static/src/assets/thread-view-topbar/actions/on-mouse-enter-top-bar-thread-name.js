/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            ThreadViewTopbar/onMouseEnterTopBarThreadName
        [Action/params]
            record
                [type]
                    ThreadViewTopbar
            ev
                [type]
                    MouseEvent
        [Action/behavior]
            {if}
                @record
                .{ThreadViewTopbar/thread}
                .{isFalsy}
                .{|}
                    @record
                    .{ThreadViewTopbar/thread}
                    .{Thread/isChannelRenamable}
                    .{isFalsy}
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                [1]
                    [ThreadViewTopbar/isMouseOverThreadName]
                        true
`;
