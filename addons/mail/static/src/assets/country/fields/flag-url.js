/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            flagUrl
        [Field/model]
            Country
        [Field/type]
            attr
        [Field/target]
            String
        [Field/compute]
            {if}
                @record
                .{Country/code}
                .{isFalsy}
            .{then}
                {Record/empty}
            .{else}
                /base/static/img/country_flags/
                .{+}
                    @record
                    .{Country/code}
                .{+}
                    .png
`;
