/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            showMemberListButton
        [Element/model]
            ThreadViewTopbarComponent
        [Record/models]
            ThreadViewTopbarComponent/button
        [Element/isPresent]
           {Dev/comment}
                FIXME: guests should be able to see members but there currently is no route for it, so hide it for now
            {Env/isCurrentUserGuest}
            .{isFalsy}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{Thread/hasMemberListFeature}
                .{&}
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                    .{ThreadViewTopbar/threadView}
                    .{ThreadView/hasMemberList}
                .{&}
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                    .{ThreadViewTopbar/threadView}
                    .{ThreadView/isMemberListOpened}
        [web.Element/title]
            {Locale/text}
                Show Member List
        [Element/onClick]
            {ThreadViewTopbar/onClickShowMemberList}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
`;
