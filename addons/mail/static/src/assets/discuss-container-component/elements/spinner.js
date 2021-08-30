/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            spinner
        [Element/model]
            DiscussContainerComponent
        [Element/isPresent]
            {Discuss/discussView}
            .{isFalsy}
            .{|}
                {Env/isMessagingInitialized}
                .{isFalsy}
        [web.Element/class]
            d-flex
            flex-grow-1
            align-items-center
            justify-content-center
`;
