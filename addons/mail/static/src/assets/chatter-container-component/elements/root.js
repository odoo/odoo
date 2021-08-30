/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            root
        [Element/model]
            ChatterContainerComponent
        [web.Element/style]
            [web.scss/display]
                flex
            [web.scss/flex]
                1
                1
                auto
            [web.scss/width]
                {scss/map-get}
                    {scss/$sizes}
                    100
            {if}
                @record
                .{ChatterContainerComponent/isInFormSheetBg}
            .{then}
                [web.scss/max-width]
                    {scss/$o-form-view-sheet-max-width}
                [web.scss/margin]
                    0
                    auto
`;
