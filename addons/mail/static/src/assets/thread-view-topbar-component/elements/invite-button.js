/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            inviteButton
        [Element/model]
            ThreadViewTopbarComponent
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
            .{&}
                @record
                .{ThreadViewTopbarComponent/threadViewTopbar}
                .{ThreadViewTopbar/thread}
                .{Thread/hasInviteFeature}
        [web.Element/tag]
            button
        [web.Element/title]
            {Locale/text}
                Add users
        [Element/onClick]
            {ThreadViewTopbar/onClickInviteButton}
                [0]
                    @record
                    .{ThreadViewTopbarComponent/threadViewTopbar}
                [1]
                    @ev
`;