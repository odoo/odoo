/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadNameInput
        [Element/model]
            ThreadViewTopbarComponent
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/isEditingThreadName}
        [web.Element/tag]
            input
        [web.Element/class]
            lead
            font-weight-bold
        [web.Element/type]
            text
        [web.Element/value]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/pendingThreadName}
        [Element/onInput]
            {ThreadViewTopBar/onInputThreadNameInput}
                [0]
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                [1]
                    @ev
        [Element/onKeydown]
            {threadViewTopbar/onKeyDownThreadNameInput}
                [0]
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                [1]
                    @ev
`;