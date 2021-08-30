/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            MessagingMenuComponent
        [web.Element/class]
            dropdown
            {if}
                @record
                .{MessagingMenuComponent/messagingMenu}
                .{MessagingMenu/isOpen}
            .{then}
                show
        [web.Element/style]
            {if}
                @record
                .{MessagingMenuComponent/messagingMenu}
                .{MessagingMenu/isOpen}
            .{then}
                [web.scss/background-color]
                    {scss/rgba}
                        {scss/$black}
                        0.1
`;
