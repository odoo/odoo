/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            actions
        [Element/model]
            ChatterTopbarComponent
        [web.Element/style]
            [web.scss/border-bottom]
                {scss/$border-width}
                solid
            [web.scss/display]
                flex
            [web.scss/flex]
                1
            [web.scss/flex-direction]
                row
            [web.scss/flex-wrap]
                wrap-reverse
                {Dev/comment}
                    reverse to ensure send buttons are directly above composer
            [web.scss/border-color]
                transparent
            {if}
                @record
                .{ChatterTopbarComponent/chatter}
                .{Chatter/composerView}
            .{then}
                [web.scss/border-color]
                    {scss/$border-color}
`;
