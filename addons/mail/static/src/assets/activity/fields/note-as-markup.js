/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            noteAsMarkup
        [Field/model]
            Activity
        [Field/type]
            attr
        [Field/type]
            Markup
        [Field/compute]
            {Record/insert}
                [Record/models]
                    Markup
                @record
                .{Activity/note}
`;
