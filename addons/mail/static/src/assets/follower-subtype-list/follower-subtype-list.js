/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FollowerSubtypeList
        [Model/fields]
            component
            dialogOwner
            follower
        [Model/id]
            FollowerSubtypeList/dialogOwner
        [Model/actions]
            FollowerSubtypeList/containsElement
`;
