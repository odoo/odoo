/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            user
        [Element/model]
            ActivityComponent
        [web.Element/class]
            position-relative
`;
