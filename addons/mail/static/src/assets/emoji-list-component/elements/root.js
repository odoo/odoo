/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            EmojiListComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex-flow]
                row wrap
            [web.scss/max-width]
                200
                px
`;
