/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FollowerComponent
        [Model/fields]
            follower
        [Model/template]
            root
                details
                    avatar
                    name
                editButton
                    editButtonIcon
                removeButton
                    removeButtonIcon
`;
