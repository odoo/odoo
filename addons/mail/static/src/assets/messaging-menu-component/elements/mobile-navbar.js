/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            mobileNavbar
        [Element/model]
            MessagingMenuComponent
        [Field/target]
            MobileMessagingNavbarComponent
        [Element/isPresent]
            {Messaging/mobileMessagingNavbarView}
        [MobileMessagingNavbarComponent/mobileMessagingNavbarView]
            {MessagingMenu/mobileMessagingNavbarView}
`;
