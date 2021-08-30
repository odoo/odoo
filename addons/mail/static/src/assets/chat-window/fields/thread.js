/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the 'Thread' that should be displayed by 'this'.
        If no 'Thread' is linked, 'this' is considered "new message".
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            thread
        [Field/model]
            ChatWindow
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/inverse]
            Thread/chatWindow
        [Field/isReadonly]
            true
`;
