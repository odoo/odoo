/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether this partner is online.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isOnline
        [Field/model]
            Partner
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Collection
                online
                away
            .{Collection/includes}
                @record
                .{Partner/imStatus}
`;
