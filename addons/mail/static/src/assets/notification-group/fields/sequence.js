/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the position of the group inside the notification list.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            sequence
        [Field/model]
            NotificationGroup
        [Field/type]
            attr
        [Field/target]
            Number
        [Field/default]
            0
        [Field/compute]
            0
            .{-}
                {Math/max}
                    @record
                    .{NotificationGroup/notifications}
                    .{Collection/map}
                        {Record/insert}
                            [Record/models]
                                Function
                            [Function/in]
                                item
                            [Function/out]
                                @item
                                .{Notification/message}
                                .{Message/id}
`;
