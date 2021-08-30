/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Type of the related channel thread.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            channelType
        [Field/model]
            DiscussSidebarCategoryItem
        [Field/type]
            attr
        [Field/related]
            DiscussSidebarCategoryItem/channel
            Thread/channelType
`;
