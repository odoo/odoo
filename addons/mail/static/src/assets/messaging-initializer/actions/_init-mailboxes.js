/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            MessagingInitializer/_initMailboxes
        [Action/params]
            messagingInitializer
                [type]
                    MessagingInitializer
            needaction_inbox_counter
                [type]
                    Integer
            starred_counter
                [type]
                    Integer
        [Action/behavior]
            {Record/update}
                [0]
                    {Env/inbox}
                [1]
                    [Thread/counter]
                        @needaction_inbox_counter
            {Record/update}
                [0]
                    {Env/starred}
                [1]
                    [Thread/counter]
                        @starred_counter
`;
