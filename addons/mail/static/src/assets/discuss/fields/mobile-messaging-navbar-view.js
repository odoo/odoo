/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The navbar view on the discuss app when in mobile and when not
        replying to a message from inbox.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mobileMessagingNavbarView
        [Field/model]
            Discuss
        [Field/type]
            one
        [Field/target]
            MobileMessagingNavbarView
        [Field/isCausal]
            true
        [Field/inverse]
            MobileMessagingNavbarView/discuss
        [Field/compute]
            {if}
                {Device/isMobile}
                .{&}
                    {Discuss/threadView}
                    .{isFalsy}
                    .{|}
                        {Discuss/threadView}
                        .{ThreadView/replyingToMessageView}
                        .{isFalsy}
            .{then}
                {Record/insert}
                    [Record/models]
                        MobileMessagingNavbarView
            .{else}
                {Record/empty}
`;
