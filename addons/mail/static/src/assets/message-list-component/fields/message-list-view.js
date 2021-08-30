/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageListView
        [Field/model]
            MessageListComponent
        [Field/type]
            one
        [Field/target]
            MessageListView
        [Field/isRequired]
            true
        [Field/inverse]
            MessageListView/component
`;
