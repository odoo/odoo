/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Date of end of the out of office period of the partner as string.
        String is expected to use Odoo's date string format
        (examples: '2011-12-01' or '2011-12-01').
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            outOfOfficeDateEnd
        [Field/feature]
            hr_holidays
        [Field/model]
            Partner
        [Field/type]
            attr
        [Field/target]
            Date
        [Field/default]
            {Record/insert}
                [Record/models]
                    Date
`;
