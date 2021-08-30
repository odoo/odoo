/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageReactionGroupComponent
        [Model/fields]
            messageReactionGroup
        [Model/template]
            root
                content
                count
`;
