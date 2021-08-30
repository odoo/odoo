/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines whether the guest's name has been updated.

        Useful to determine whether a RPC should be done to update the name
        server side.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasGuestNameChanged
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/readonly]
            true
        [Field/compute]
            {Env/currentGuest}
            .{&}
                @record
                .{ThreadViewTopbar/pendingGuestName}
                .{!=}
                    {Env/currentGuest}
                    .{Guest/name}
`;
