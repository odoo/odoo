/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether 'this' is focused. Useful for visual clue.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isFocused
        [Field/model]
            ChatWindow
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
