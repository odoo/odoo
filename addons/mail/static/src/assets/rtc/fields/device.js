/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            device
        [Field/model]
            Rtc
        [Field/type]
            one
        [Field/target]
            Device
        [Field/default]
            {Env/device}
        [Field/observe]
            {Record/insert}
                [Record/models]
                    FieldObserver
                [FieldObserver/event]
                    keydown
                [FieldObserver/callback]
                    {Rtc/onKeydown}
                        @ev
            {Record/insert}
                [Record/models]
                    FieldObserver
                [FieldObserver/event]
                    keyup
                [FieldObserver/callback]
                    {Rtc/onKeyup}
                        @ev
            {Record/insert}
                [Record/models]
                    FieldObserver
                [FieldObserver/event]
                    beforeunload
                [FieldObserver/callback]
                    {if}
                        {Rtc/channel}
                    .{then}
                        {Thread/performRpcLeaveCall}
                            {Rtc/channel}
`;
