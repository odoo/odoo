/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the search term used to filter this list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            searchTerm
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            attr
        [Field/target]
            String
`;