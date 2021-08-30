/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _subtypesListDialog
        [Field/model]
            Follower
        [Field/type]
            one
        [Field/target]
            FollowerSubtypeList
`;
