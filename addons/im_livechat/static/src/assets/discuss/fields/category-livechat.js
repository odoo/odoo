/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Discuss sidebar category for 'livechat' channel threads.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            categoryLivechat
        [Field/model]
            Discuss
        [Field/feature]
            im_livechat
        [Field/type]
            one
        [Field/target]
            DiscussSidebarCategory
        [Field/inverse]
            DiscussSidebarCategory/discussAsLivechat
        [Field/isCausal]
            true
`;
