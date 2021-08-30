/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Leaves the current call if there is one, joins the call if the user was
        not yet in it.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            Thread/toggleCall
        [Action/params]
            options
                [type]
                    Object
            record
                [type]
                    Thread
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [Thread/hasPendingRtcRequest]
                        true
            :isActiveCall
                @record
                .{Thread/rtc}
                .{isTruthy}
            {if}
                {Rtc/channel}
            .{then}
                {Thread/leaveCall}
                    {Rtc/channel}
            {if}
                @isActiveCall
            .{then}
                {Record/update}
                    [0]
                        @record
                    [1]
                        [Thread/hasPendingRtcRequest]
                            false
                {break}
            {Thread/_joinCall}
                [0]
                    @record
                [1]
                    @options
            {Record/update}
                [0]
                    @record
                [1]
                    [Thread/hasPendingRtcRequest]
                        false
`;
