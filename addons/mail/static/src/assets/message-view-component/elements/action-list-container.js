/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actionListContainer
        [Element/model]
            MessageViewComponent
        [Element/isPresent]
            @record
            .{MessageViewComponent/messageView}
            .{MessageView/messageActionList}
            .{&}
                @record
                .{MessageViewComponent/isActive}
        [web.Element/class]
            pl-5
            pr-3
        [web.Element/style]
            {web.scss/include}
                {web.scss/o-position-absolute}
                    [$top]
                        {-}
                            {scss/map-get}
                                {scss/$spacers}
                                3
                    [$right]
                        0
            {if}
                @record
                .{MessageViewComponent/messageView}
                .{MessageView/isSquashed}
            .{then}
                {web.scss/include}
                    {web.scss/o-position-absolute}
                        [$top]
                            {-}
                                {scss/map-get}
                                    {scss/$spacers}
                                    4
                        [$right]
                            0
`;
