/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        The title text in UI for command 'add'
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            commandAddTitleText
        [Field/model]
            DiscussSidebarCategory
        [Field/type]
            attr
        [Field/target]
            String
`;
