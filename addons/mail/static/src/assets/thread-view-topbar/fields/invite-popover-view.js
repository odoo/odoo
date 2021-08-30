/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            invitePopoverView
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            one
        [Field/target]
            PopoverView
        [Field/isCausal]
            true
        [Field/inverse]
            PopoverView/threadViewTopbarOwnerAsInvite
`;
