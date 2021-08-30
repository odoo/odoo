/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FollowerSubtypeComponent
        [Model/fields]
            follower
            followerSubtype
        [Model/template]
            root
                label
                    checkbox
                    text
`;
