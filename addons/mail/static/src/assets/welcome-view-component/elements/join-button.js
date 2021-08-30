/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            joinButton
        [Element/model]
            WelcomeViewComponent
        [web.Element/tag]
            button
        [web.Element/class]
            btn
            btn-success
            btn-lg
            align-self-end
            p-0
            rounded-circle
            shadow
            fa
            fa-phone
        [web.Element/title]
            {Locale/text}
                Join Channel
        [web.Element/isDisabled]
            @record
            .{WelcomeViewComponent/welcomeView}
            .{WelcomeView/isJoinButtonDisabled}
        [Element/onClick]
            {WelcomeView/onClickJoinButton}
                [0]
                    @record
                    .{WelcomeViewComponent/welcomeView}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/height]
                4
                rem
            [web.scss/width]
                4
                rem
            [web.scss/font-size] 
                2
                em
            [web.scss/line-height]
                4
                rem
`;
