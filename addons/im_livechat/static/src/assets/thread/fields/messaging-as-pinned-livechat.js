/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, current thread is a livechat.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messagingAsPinnedLivechat
        [Field/model]
            Thread
        [Field/feature]
            im_livechat
        [Field/type]
            one
        [Field/target]
            Env
        [Field/inverse]
            Env/pinnedLivechats
        [Field/compute]
            {if}
                @record
                .{Thread/channelType}
                .{!=}
                    livechat
                .{|}
                    @record
                    .{Thread/isPinned}
                    .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                @env
`;
