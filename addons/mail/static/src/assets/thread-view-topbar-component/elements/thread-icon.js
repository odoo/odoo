/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            threadIcon
        [Element/model]
            ThreadViewTopbarComponent
        [Field/target]
            ThreadIconComponent
        [web.Element/class]
            mr-2
            align-self-center
        [ThreadIconComponent/thread]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
        [Element/isPresent]
            @record
            .{ThreadViewTopbarComponent/threadViewTopbar}
            .{ThreadViewTopbar/thread}
`;
