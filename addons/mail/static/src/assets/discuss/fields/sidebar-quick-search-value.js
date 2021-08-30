/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Quick search input value in the discuss sidebar (desktop). Useful
        to filter channels and chats based on this input content.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            sidebarQuickSearchValue
        [Field/model]
            Discuss
        [Field/type]
            attr
        [Field/target]
            String
`;
