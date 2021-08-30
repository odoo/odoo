/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            activeThread
        [Field/model]
            Composer
        [Field/type]
            one
        [Field/target]
            Thread
        [Field/isReadonly]
            true
        [Field/isRequired]
            true
        [Field/compute]
            {if}
                @record
                .{Composer/messageViewInEditing}
                .{&}
                    @record
                    .{Composer/messageViewInEditing}
                    .{MessageView/message}
                .{&}
                    @record
                    .{Composer/messageViewInEditing}
                    .{MessageView/message}
                    .{Message/originThread}
            .{then}
                @record
                .{Composer/messageViewInEditing}
                .{MessageView/message}
                .{Message/originThread}
            .{elif}
                @record
                .{Composer/thread}
            .{then}
                @record
                .{Composer/thread}
            .{else}
                {Record/empty}
`;
