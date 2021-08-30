/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            group
        [Field/model]
            Notification
        [Field/type]
            one
        [Field/target]
            NotificationGroup
        [Field/inverse]
            NotificationGroup/notifications
        [Field/compute]
            {if}
                @record
                .{Notification/isFailure}
                .{isFalsy}
                .{|}
                    @record
                    .{Notification/isFromCurrentUser}
                    .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                :thread
                    @record
                    .{Notification/message}
                    .{Message/originThread}
                {Dev/comment}
                    Notifications are grouped by model and notification_type.
                    Except for channel where they are also grouped by id because
                    we want to open the actual channel in discuss or chat window
                    and not its kanban/list/form view.
                {Record/insert}
                    [Record/models]
                        NotificationGroup
                    [NotificationGroup/type]
                        @record
                        .{Notification/type}
                    [NotificationGroup/resId]
                        {if}
                            @thread
                            .{Thread/model}
                            .{=}
                                mail.channel
                        .{then}
                            @thread
                            .{Thread/id}
                        .{else}
                            null
                    [NotificationGroup/resModel]
                        @thread
                        .{Thread/model}
                    [NotificationGroup/resModelName]
                        @thread
                        .{Thread/modelName}
`;
