/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ChannelMemberListComponent
        [web.Element/class]
            d-flex
            flex-column
            overflow-
            bg-light
        [web.Element/style]
            [overflow-y]
                auto
`;
