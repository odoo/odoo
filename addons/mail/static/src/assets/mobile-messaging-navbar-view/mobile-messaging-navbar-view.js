/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MobileMessagingNavbarView
        [Model/fields]
            activeTabId
            discuss
            messagingMenu
            tabs
        [Model/id]
            MobileMessagingNavbarView/discuss
            .{|}
                MobileMessagingNavbarView/messagingMenu
        [Model/actions]
            MobileMessagingNavbarView/onClick
`;
