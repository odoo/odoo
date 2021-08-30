/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Toggle whether the messaging menu is open or not.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingMenu/toggleOpen
        [Action/params]
            messagingMenu
                [type]
                    MessagingMenu
        [Action/behavior]
            {Record/update}
                [0]
                    @messagingMenu
                [1]
                    [MessagingMenu/isOpen]
                        {MessagingMenu/isOpen}
                        .{isFalsy}
            {Env/refreshIsNotificationPermissionDefault}
            {if}
                {MessagingMenu/isOpen}
            .{then}
                {Dev/comment}
                    populate some needaction messages on threads.
                {Record/update}
                    [0]
                        {Env/inbox}
                        .{Thread/cache}
                    [1]
                        [ThreadCache/isCacheRefreshRequested]
                            true
`;
