/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toggler
        [Element/model]
            MessagingMenuComponent
        [web.Element/tag]
            a
        [web.Element/href]
            #
        [web.Element/title]
            {Locale/text}
                Conversations
        [web.Element/role]
            button
        [web.Element/aria-expanded]
            @record
            .{MessagingMenuComponent/messagingMenu}
            .{MessagingMenu/isOpen}
        [web.Element/aria-haspopup]
            true
        [Element/onClick]
            {Dev/comment}
                avoid following dummy href
            {web.Event/preventDefault}
                @ev
            {MessagingMenu/toggleOpen}
                @record
                .{MessagingMenuComponent/messagingMenu}
        [web.Element/class]
            dropdown-toggle
            o-no-caret
            o-dropdown--narrow
        [web.Element/style]
            {if}
                @record
                .{MessagingMenuComponent/messagingMenu}
                .{MessagingMenu/counter}
                .{=}
                    0
            .{then}
                {web.scss/include}
                    {web.scss/o-mail-systray-no-notification-style}
`;
