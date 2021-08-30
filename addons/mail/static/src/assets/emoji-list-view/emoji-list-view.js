/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            EmojiListView
        [Model/id]
            EmojiListView/popoverViewOwner
        [Model/fields]
            popoverViewOwner
        [Model/actions]
            EmojiListView/onClickEmoji
`;
