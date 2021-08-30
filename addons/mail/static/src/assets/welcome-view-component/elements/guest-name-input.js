/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            guestNameInput
        [Element/model]
            WelcomeViewComponent
        [Element/isPresent]
            {Env/currentGuest}
        [web.Element/tag]
            input
        [web.Element/class]
            form-control
            mb-3
        [web.Element/type]
            text
        [web.Element/placeholder]
            {Locale/text}
                Your name
        [web.Element/name]
            @record
            .{WelcomeViewComponent/welcomeView}
            .{WelcomeView/guestNameInputUniqueId}
        [web.Element/id]
            @record
            .{WelcomeViewComponent/welcomeView}
            .{WelcomeView/guestNameInputUniqueId}
        [web.Element/value]
            @record
            .{WelcomeViewComponent/welcomeView}
            .{WelcomeView/pendingGuestName}
        [Element/onInput]
            {WelcomeView/onInputGuestNameInput}
                [0]
                    @record
                    .{WelcomeViewComponent/welcomeView}
                [1]
                    @ev
        [Element/onKeydown]
            {WelcomeView/onKeydownGuestNameInput}
                [0]
                    @record
                    .{WelcomeViewComponent/welcomeView}
                [1]
                    @ev
`;
