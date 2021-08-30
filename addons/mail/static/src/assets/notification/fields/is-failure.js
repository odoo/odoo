/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isFailure
        [Field/model]
            Notification
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Collection
                exception
                bounce
            .{Collection/includes}
                @record
                .{Notification/status}
`;
