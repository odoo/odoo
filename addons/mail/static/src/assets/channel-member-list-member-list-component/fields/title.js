/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            title
        [Field/model]
            ChannelMemberListMemberListComponent
        [Field/type]
            attr
        [Field/target]
            String
`;
