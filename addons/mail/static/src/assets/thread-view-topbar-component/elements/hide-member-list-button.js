/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            hideMemberListButton
        [Element/model]
            ThreadViewTopbarComponent
        [Record/models]
            ThreadViewTopbarComponent/button
        [Element/isPresent]
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
                .{isFalsy}
        [web.Element/title]
            {Locale/text}
                Hide Member List
        [Element/onClick]
            {ThreadViewTopbar/onClickHideMemberList}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
`;
