/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            SuggestedRecipientInfo
        [Model/fields]
            email
            id
            isSelected
            name
            partner
            reason
            thread
        [Model/id]
            SuggestedRecipientInfo/id
`;
