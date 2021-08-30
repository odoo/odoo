/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether this search input needs to be focused.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            doFocusOnSearchInput
        [Field/model]
            ChannelInvitationForm
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;