/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Ordered list of tabs that this navbar has.
        Format of tab:
        {
            icon: <the classname for this tab>
            id: <the id for this tab>
            label: <the label/name of this tab>
        }
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            tabs
        [Field/model]
            MobileMessagingNavbarView
        [Field/type]
            attr
        [Field/target]
            Collection<Object>
        [Field/compute]
            {if}
                @record
                .{MobileMessagingNavbarView/discuss}
            .{then}
                {Record/insert}
                    [Record/models]
                        Collection
                    []
                        [icon]
                            fa
                            fa-inbox
                        [id]
                            mailbox
                        [label]
                            {Locale/text}
                                Mailboxes
                    []
                        [icon]
                            fa
                            fa-user
                        [id]
                            chat
                        [label]
                            {Locale/text}
                                Chat
                    []
                        [icon]
                            fa
                            fa-users
                        [id]
                            channel
                        [label]
                            {Locale/text}
                                Channel
            .{elif}
                @record
                .{MobileMessagingNavbarView/messagingMenu}
            .{then}
                {Record/insert}
                    [Record/models]
                        Collection
                    []
                        [icon]
                            fa
                            fa-envelope
                        [id]
                            all
                        [label]
                            {Locale/text}
                                All
                    []
                        [icon]
                            fa
                            fa-user
                        [id]
                            chat
                        [label]
                            {Locale/text}
                                Chat
                    []
                        [icon]
                            fa
                            fa-users
                        [id]
                            channel
                        [label]
                            {Locale/text}
                                Channel
            .{else}
                {Record/insert}
                    [Record/models]
                        Collection
`;
