/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether this message can be starred/unstarred.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            canStarBeToggled
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Env/isCurrentUserGuest}
            .{isFalsy}
            .{&}
                @record
                .{Message/isTemporary}
                .{isFalsy}
                .{&}
                    @record
                    .{Message/isTransient}
                    .{isFalsy}
`;
