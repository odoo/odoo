/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            pttRegisteringButton
        [Element/model]
            RtcConfigurationMenuComponent
        [web.Element/tag]
            button
        [Element/onClick]
            {RtcConfigurationMenuComponent/onClickRegisterKeyButton}
                [0]
                    @record
                [1]
                    @ev
        [web.Element/style]
            [web.scss/background]
                none
            [web.scss/border]
                none
            [web.scss/outline]
                none
            {web.scss/include}
                {scss/hover-focus}
                    [web.scss/outline]
                        none
            {if}
                @field
                .{web.Element/isHover}
            .{then}
                [web.scss/color]
                    black
`;
