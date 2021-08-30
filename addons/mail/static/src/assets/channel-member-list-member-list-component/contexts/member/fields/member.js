/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            member
        [Field/model]
            ChannelMemberListMemberListComponent
        [Field/type]
            one
        [Field/target]
            Partner
        [Field/isRequired]
            true
`;
