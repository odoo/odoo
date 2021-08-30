/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, this popover view is owned by a thread view topbar record.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadViewTopbarOwnerAsInvite
        [Field/model]
            PopoverView
        [Field/type]
            one
        [Field/target]
            ThreadViewTopbar
        [Field/isReadonly]
            true
        [Field/inverse]
            ThreadViewTopbar/invitePopoverView
`;
