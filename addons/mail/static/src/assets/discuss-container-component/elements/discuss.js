/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            discuss
        [Element/model]
            DiscussContainerComponent
        [Element/isPresent]
            {Discuss/discussView}
            .{&}
                {Env/isMessagingInitialized}
        [web.Element/class]
            flex-grow-1
        [Field/target]
            DiscussComponent
        [DiscussComponent/discussView]
            {Discuss/discussView}
`;
