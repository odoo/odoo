/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Channel type which is supported by the category.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            supportedChannelTypes
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
`;
