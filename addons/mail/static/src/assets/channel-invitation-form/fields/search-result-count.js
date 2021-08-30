/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the number of results of the last search.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            searchResultCount
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
`;