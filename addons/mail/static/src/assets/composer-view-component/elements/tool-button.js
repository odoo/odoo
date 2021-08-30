/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            toolButton
        [Element/model]
            ComposerViewComponent
        [web.Element/style]
            {Dev/comment}
                keep a margin between the buttons to prevent their focus shadow from overlapping
            [web.scss/margin-left]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/margin-right]
                {scss/map-get}
                    {scss/$spacers}
                    1
            [web.scss/border]
                0
                {Dev/comment}
                    overrides bootstrap btn
            [web.scss/background-color]
                {scss/$white}
                {Dev/comment}
                    overrides bootstrap btn-light
            [web.scss/color]
                {scss/gray}
                    600
                    {Dev/comment}
                        overrides bootstrap btn-light
            [web.scss/border-radius]
                50%
            {if}
                @record
                .{ComposerViewComponent/messagingMenu}
                .{MessagingMenu/isOpen}
            .{then}
                [web.scss/background-color]
                    {scss/gray}
                        200
`;
