/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            command
        [Element/model]
            MessageViewComponent
        [web.Element/tag]
            span
        [Record/models]
            Hoverable
        [web.Element/style]
            [web.scss/cursor]
                pointer
            [web.scss/color]
                {scss/gray}
                    400
            {if}
                {Device/isMobile}
                .{isFalsy}
                .{&}
                    @field
                    .{web.Element/isHover}
            .{then}
                [web.scss/filter]
                    {web.scss/brightness}
                        0.8
            {if}
                {Device/isMobile}
            .{then}
                [web.scss/filter]
                    {web.scss/brightness}
                        0.8
                {if}
                    @field
                    .{web.Element/isHover}
                .{then}
                    [web.scss/filter]
                        {web.scss/brightness}
                            0.75
            {if}
                @record
                .{MessageViewComponent/isSelected}
            .{then}
                [web.scss/color]
                    {scss/gray}
                        500
`;
