/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Attempts a connection recovery by closing and restarting the call
        from the receiving end.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Rtc/_recoverConnection
        [Action/params]
            token
                [type]
                    String
            delay
                [type]
                    Integer
                [default]
                    0
                [description]
                    delay in ms
            reason
                [type]
                    String
            record
                [type]
                    Rtc
        [Action/behavior]
            {if}
                @record
                .{Rtc/_fallBackTimeouts}
                .{Collection/at}
                    @token
            .{then}
                {break}
            {Record/update}
                [0]
                    @record
                    .{Rtc/_fallBackTimeouts}
                [1]
                    {entry}
                        [key]
                            @token
                        [value]
                            {Browser/setTimeout}
                                [0]
                                    {Rtc/_onRecovertConnectionTimeout}
                                        [0]
                                            @record
                                        [1]
                                            @token
                                        [2]
                                            @reason
                            [1]
                                @delay
`;
