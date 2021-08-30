/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadDescriptionInput
        [Element/model]
            ThreadViewTopbarComponent
        [web.Element/tag]
            input
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{Thread/isChannelDescriptionChangeable}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/isEditingThreadDescription}
        [web.Element/type]
            text
        [web.Element/value]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/pendingThreadDescription}
        [Element/onInput]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/onInputThreadDescriptionInput}
                @ev
        [Element/onKeydown]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/onKeyDownThreadDescriptionInput}
                @ev
`;