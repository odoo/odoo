/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Closes the category and notity server to change the state
    {Record/insert}
        [Record/models]
            Action
        [Action/name]
            DiscussSidebarCategory/close
        [Action/params]
            record
                [type]
                    DiscussSidebarCategory
        [Action/behavior]
            {Record/update}
                [0]
                    @record
                [1]
                    [DiscussSidebarCategory/isPendingOpen]
                        false
            {DiscussSidebarCategory/performRpcSetResUsersSettings}
                {entry}
                    [key]
                        @record
                        .{DiscussSidebarCategory/serverStateKey}
                    [value]
                        false
`;
