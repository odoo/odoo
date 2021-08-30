/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            DiscussMobileMailboxSelectionComponent]
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                0
                0
                auto
`;
