/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            EmojiListComponent
        [Model/fields]
            emojiListView
            emojis
        [Model/template]
            root
                emojiForeach
        [Model/actions]
            EmojiListComponent/close
            EmojiListComponent/contains
        [Model/lifecycles]
            onUpdate
`;
