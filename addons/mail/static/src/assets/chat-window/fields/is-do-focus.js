/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determine whether the chat window should be programmatically
        focused by observed component of chat window. Those components
        are responsible to unmark this record afterwards, otherwise
        any re-render will programmatically set focus again!
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isDoFocus
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
