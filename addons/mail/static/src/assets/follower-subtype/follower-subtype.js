/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FollowerSubtype
        [Model/fields]
            id
            isDefault
            isInternal
            name
            parentModel
            resModel
            sequence
        [Model/id]
            FollowerSubtype/id
        [Model/actions]
            FollowerSubtype/convertData
`;
