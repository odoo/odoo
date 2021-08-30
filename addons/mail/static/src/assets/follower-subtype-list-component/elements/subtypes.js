/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Element
        [Element/name]
            subtypes
        [Element/model]
            FollowerSubtypeListComponent
`;
