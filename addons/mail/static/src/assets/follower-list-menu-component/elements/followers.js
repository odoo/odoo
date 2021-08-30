/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            followers
        [Element/model]
            FollowerListMenuComponent
        [web.Element/style]
            [web.scss/display]
                flex
`;
