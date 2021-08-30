/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether this thread has the seen indicators (V and VV)
        enabled or not.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasSeenIndicators
        [Field/model]
            Thread
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
        [Field/compute]
            {if}
                @record
                .{Thread/model}
                .{!=}
                    mail.channel
            .{then}
                false
            .{else}
                {Record/insert}
                    [Record/models]
                        Collection
                    chat
                    livechat
                .{Collection/includes}
                    @record
                    .{Thread/channelType}
`;
