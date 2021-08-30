/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the time elapsed since date up to now.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            dateFromNow
        [Field/model]
            Message
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Message/date}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                {Utils/timeFromNow}
                    @record
                    .{Message/date}
`;
