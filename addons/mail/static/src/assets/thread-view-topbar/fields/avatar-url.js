/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the URL of the profile picture of the current user.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            avatarUrl
        [Field/model]
            ThreadViewTopbar
        [Field/type]
            attr
        [Field/target]
            String
        [Field/isReadonly]
            true
        [Field/compute]
            {if}
                {Env/isCurrentUserGuest}
            .{then}
                {if}
                    @record
                    .{ThreadViewTopbar/thread}
                    .{isFalsy}
                .{then}
                    {String/empty}
                .{else}
                    /mail/channel/
                    .{+}
                        @record
                        .{ThreadViewTopbar/thread}
                        .{Thread/id}
                    .{+}
                        /guest/
                    .{+}
                        {Env/currentGuest}
                        .{Guest/id}
                    .{+}
                        /avatar_128?unique=
                    .{+}
                        {Env/currentGuest}
                        .{Guest/name}
            .{else}
                {Env/currentPartner}
                .{Partner/avatarUrl}
`;
