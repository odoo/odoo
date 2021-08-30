/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagingAsRingingThread
        [Field/model]
            Thread
        [Field/type]
            one
        [Field/target]
            Env
        [Field/isReadonly]
            true
        [Field/inverse]
            Env/ringingThreads
        [Field/compute]
            {if}
                @record
                .{Thread/rtcInvitingSession}
            .{then}
                @env
            .{else}
                {Record/empty}
`;
