/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            ActionAddon
        [ActionAddon/action]
            Partner/convertData
        [ActionAddon/feature]
            hr_holidays
        [ActionAddon/params]
            data
        [ActionAddon/behavior]
            :data2
                @original
            {if}
                @data
                .{Dict/hasKey}
                    out_of_office_date_end
                .{&}
                    @data
                    .{Dict/get}
                        date
            .{then}
                {Record/update}
                    [0]
                        @data2
                    [1]
                        [Partner/outOfOfficeDateEnd]
                            {Record/insert}
                                [Record/models]
                                    Date
                                {String/toDatetime}
                                    @data
                                    .{Dict/get}
                                        out_of_office_date_end
            @data2
`;
