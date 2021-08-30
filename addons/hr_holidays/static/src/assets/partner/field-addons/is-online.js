/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            FieldAddon
        [FieldAddon/field]
            Partner/isOnline
        [FieldAddon/feature]
            hr_holidays
        [FieldAddon/compute]
            {if}
                {Record/insert}
                    [Record/models]
                        Collection
                    leave_online
                    leave_away
                .{Collection/includes}
                    @record
                    .{Partner/imStatus}
            .{then}
                true
            .{else}
                @original
`;
