/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Discuss sidebar category for 'channel' type channel threads.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            categoryChannel
        [Field/model]
            Discuss
        [Field/type]
            one
        [Field/target]
            DiscussSidebarCategory
        [Field/isCausal]
            true
        [Field/inverse]
            DiscussSidebarCategory/discussAsChannel
`;
