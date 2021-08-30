/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Toggle the visibility of the messaging menu "new message" input in
        mobile.
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingMenu/toggleMobileNewMessage
        [Action/params]
            messagingMenu
                [type]
                    MessagingMenu
        [Action/behavior]
            {Record/update}
                [0]
                    @messagingMenu
                [1]
                    [MessagingMenu/isMobileNewMessageToggled]
                        @messagingMenu
                        .{MessagingMenu/isMobileNewMessageToggled}
                        .{isFalsy}
`;
