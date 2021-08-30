/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            action
        [Field/model]
            MessageActionListComponent
        [Record/models]
            Hoverable
        [web.Element/tag]
            span
        [web.Element/class]
            fa
            fa-lg
            p-2
        [web.Element/style]
            [web.scss/cursor]
                pointer
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/background-color]
                    {web.scss/mix}
                        {scss/$border-color}
                        {scss/$white}
`;
