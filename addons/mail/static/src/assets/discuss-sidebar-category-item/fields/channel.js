/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The related channel thread.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channel
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/inverse]
            Tread/discussSidebarCategoryItem
`;
