/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            guestNameLabel
        [Element/model]
            WelcomeViewComponent
        [Element/isPresent]
            {Env/currentGuest}
        [web.Element/tag]
            label
        [web.Element/class]
            text-center
        [web.Element/for]
            @record
            .{WelcomeViewComponent/welcomeView}
            .{WelcomeView/guestNameInputUniqueId}
        [web.Element/textContent]
            {Locale/text}
                What's your name?
        [web.Element/style]
            [web.scss/font-size]
                {scss/$font-size-lg}
`;
