/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Discuss sidebar category for 'chat' type channel threads.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            categoryChat
        [Field/model]
            Discuss
        [Field/type]
            one
        [Field/target]
            DiscussSidebarCategory
        [Field/isCausal]
            true
        [Field/inverse]
            DiscussSidebarCategory/discussAsChat
`;
