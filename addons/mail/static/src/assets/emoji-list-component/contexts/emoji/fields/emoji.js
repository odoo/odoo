/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            emoji
        [Field/model]
            EmojiListComponent:emoji
        [Field/type]
            one
        [Field/target]
            Emoji
`;
