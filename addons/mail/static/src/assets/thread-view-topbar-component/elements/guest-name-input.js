/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            guestNameInput
        [Element/model]
            ThreadViewTopbarComponent
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/isEditingGuestName}
        [web.Element/tag]
            input
        [web.Element/type]
            text
        [web.Element/value]
            {Env/currentGuest}
            .{Guest/name}
        [Element/onInput]
            {ThreadViewTopbar/onInputGuestNameInput}
                [0]
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                [1]
                    @ev
        [Element/onKeydown]
            {ThreadViewTopbar/onKeydownGuestNameInput}
                [0]
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                [1]
                    @ev
        [web.Element/style]
            [web.scss/width]
                150
                px
`;
