/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            emoji
        [Context/model]
            EmojiListComponent
        [Model/fields]
            emoji
        [Model/template]
            emojiForeach
                emoji
`;
