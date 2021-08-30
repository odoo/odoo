/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the sorting method of channels in this category.
        Must be one of: 'name', 'last_action'.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            sortComputeMethod
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/isRequired]
            true
`;
