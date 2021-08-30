/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            RtcSession/_debounce
        [Action/params]
            f
                [type]
                    Function
            delay
                [type]
                    Integer
            record
                [type]
                    RtcSession
        [Action/behavior]
            {if}
                @record
                .{RtcSession/_timeoutId}
            .{then}
                {Browser/clearTimeout}
                    @record
                    .{RtcSession/_timeoutId}
            {Record/update}
                [0]
                    @record
                [1]
                    [RtcSession/_timeoutId]
                        {Browser/setTimeout}
                            [0]
                                {if}
                                    {Record/exists}
                                        @record
                                    .{isFalsy}
                                .{then}
                                    {break}
                                @f
                                .{Function/call}
                            [1]
                                @delay
`;
