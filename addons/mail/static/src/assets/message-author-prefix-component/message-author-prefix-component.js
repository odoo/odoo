/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            MessageAuthorPrefixComponent
        [Model/fields]
            message
            thread
        [Model/template]
            root
                icon
                selfText
                nonSelfText
`;
