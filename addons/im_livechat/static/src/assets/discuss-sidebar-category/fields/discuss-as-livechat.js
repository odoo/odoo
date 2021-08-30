/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            discussAsLivechat
        [Field/feature]
            im_livechat
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            one
        [Field/target]
            Discuss
        [Field/inverse]
            Discuss/categoryLivechat
        [Field/isReadonly]
            true
`;
