/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        AKU TODO: make model for emojis
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            emojis
        [Field/model]
            EmojiListComponent
        [Field/type]
            one
        [Field/target]
            Emojis
        [Field/isRequired]
            true
`;
