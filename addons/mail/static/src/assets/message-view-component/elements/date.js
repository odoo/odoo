/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            date
        [Element/model]
            MessageViewComponent
        [web.Element/style]
            [web.scss/font-size]
                0.8em
            [web.scss/color]
                {scss/gray}
                    500
            {if}
                @record
                .{MessageViewComponent/isSelected}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        600
`;
