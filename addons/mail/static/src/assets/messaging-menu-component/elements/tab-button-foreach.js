/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            tabButtonForeach
        [Element/model]
            MessagingMenuComponent
        [Record/models]
            Foreach
        [Field/target]
            MessagingMenuComponent:tabButton
        [MessagingMenuComponent:tabButton/tabId]
            @field
            .{Foreach/get}
                tabId
        [Element/isPresent]
            {Device/isMobile}
            .{isFalsy}
        [Foreach/collection]
            all
            chat
            channel
        [Foreach/as]
            tabId
        [Element/key]
            @field
            .{Foreach/get}
                tabId
`;
