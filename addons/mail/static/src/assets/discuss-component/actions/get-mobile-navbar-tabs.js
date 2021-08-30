/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussComponent/getMobileNavbarTabs
        [Action/behavior]
            {Record/insert}
                [Record/models]
                    Collection
                [0]
                    {Record/insert}
                        [Record/models]
                            Dict
                        [icon]
                            fa fa-inbox
                        [id]
                            mailbox
                        [label]
                            {Locale/text}
                                Mailboxes
                [1]
                    {Record/insert}
                        [Record/models]
                            Dict
                        [icon]
                            fa fa-user
                        [id]
                            chat
                        [label]
                            {Locale/text}
                                Chat
                [2]
                    {Record/insert}
                        [Record/models]
                            Dict
                        [icon]
                            fa fa-users
                        [id]
                            channel
                        [label]
                            {Locale/text}
                                Channel
`;
