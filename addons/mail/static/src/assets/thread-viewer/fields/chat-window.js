/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatWindow
        [Field/model]
            ThreadViewer
        [Field/type]
            one
        [Field/target]
            ChatWindow
        [Field/inverse]
            ChatWindow/threadViewer
        [Field/isReadonly]
            true
`;
