/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatWindow
        [Field/model]
            ChatWindowHeaderComponent
        [Field/type]
            one
        [Field/target]
            ChatWindow
        [Field/isRequired]
            true
`;
