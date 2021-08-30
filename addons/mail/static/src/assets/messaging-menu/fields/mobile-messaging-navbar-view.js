/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The navbar view on the messaging menu when in mobile.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            mobileMessagingNavbarView
        [Field/model]
            MessagingMenu
        [Field/type]
            one
        [Field/target]
            MobileMessagingNavbarView
        [Field/isCausal]
            true
        [Field/inverse]
            MobileMessagingNavbarView/messagingMenu
        [Field/compute]
            {if}
                {Device/isMobile}
            .{then}
                {Record/insert}
                    [Record/models]
                        MobileMesagingNavbarView
            .{else}
                {Record/empty}
`;
