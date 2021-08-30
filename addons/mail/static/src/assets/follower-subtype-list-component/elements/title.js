/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            title
        [Element/model]
            FollowerSubtypeListComponent
        [web.Element/tag]
            h4
        [web.Element/class]
            modal-title
        [web.Element/textContent]
            {String/sprintf}
                [0]
                    {Locale/text}
                        Edit Subscription of %s
                [1]
                    @record
                    .{FollowerSubtypeListComponent/record}
                    .{FollowerSubtypeList/follower}
                    .{Follower/partner}
                    .{Partner/nameOrDisplayName}
`;
