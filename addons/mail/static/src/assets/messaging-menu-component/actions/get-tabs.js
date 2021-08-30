/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingMenuComponent/getTabs
        [Action/returns]
            Collection<Object>
        [Action/behavior]
            {Record/insert}
                [Record/models]
                    Collection
                [0]
                    [icon]
                        fa
                        fa-envelope
                    [id]
                        all
                    [label]
                        {Locale/text}
                            All
                [1]
                    [icon]
                        fa
                        fa-user
                    [id]
                        chat
                    [label]
                        {Locale/text}
                            Chat
                [2]
                    [icon]
                        fa
                        fa-users
                    [id]
                        channel
                    [label]
                        {Locale/text}
                            Channel
`;
