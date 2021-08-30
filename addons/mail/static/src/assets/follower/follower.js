/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            Follower
        [Model/fields]
            _subtypesListDialog
            followedThread
            followerSubtypeListDialog
            id
            isActive
            isEditable
            partner
            selectedSubtypes
            subtypes
        [Model/id]
            Follower/id
        [Model/actions]
            Follower/closeSubtypes
            Follower/convertData
            Follower/openProfile
            Follower/remove
            Follower/selectSubtype
            Follower/showSubtypes
            Follower/unselectSubtype
            Follower/updateSubtypes
`;
