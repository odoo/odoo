/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessagingMenu
        [Model/fields]
            activeTabId
            counter
            isMobileNewMessageToggled
            isOpen
            mobileMessagingNavbarView
            notificationListView
            pinnedAndUnreadChannels
        [Model/id]
            MessagingMenu/messaging
        [Model/actions]
            MessagingMenu/close
            MessagingMenu/toggleMobileNewMessage
            MessagingMenu/toggleOpen
`;
