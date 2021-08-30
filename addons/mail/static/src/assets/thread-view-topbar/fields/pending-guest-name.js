/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the pending name of the guest, which is the new name of
        the guest as the current guest is currently typing it, with the goal
        of renaming the guest.
        This value can either be applied or discarded.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            pendingGuestName
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            String
        [Field/default]
            {String/empty}
`;
