/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            subtype
        [Model/name]
            FollowerSubtypeListComponent
        [Model/fields]
            subtype
        [Model/template]
            subtypeForeach
                subtype
`;
