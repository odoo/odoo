/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            popoverViewOwner
        [Field/model]
            EmojiListView
        [Field/type]
            one
        [Field/target]
            PopoverView
        [Field/isRequired]
            true
        [Field/isReadonly]
            true
        [Field/inverse]
            PopoverView/emojiListView
`;
