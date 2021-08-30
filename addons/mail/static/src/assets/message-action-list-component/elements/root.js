/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Field/model]
            MessageActionListComponent
        [Record/models]
            Hoverable
        [Element/onClick]
            {MessageActionList/onClick}
                [0]
                    @record
                    .{MessageActionListComponent/messageActionList}
                [1]
                    @ev
        [web.Element/class]
            d-flex
        [web.Element/style]
            [web.scss/background-color]
                {scss/$white}
            [web.scss/border]
                {scss/$border-width}
                solid
                {scss/$border-color}
            [web.scss/border-radius]
                {scss/$o-mail-rounded-rectangle-border-radius-sm}
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/box-shadow]
                    0
                    4px
                    .5rem
                    -.5rem
                    black
`;
