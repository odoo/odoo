/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the component displaying this message view (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            MessageView
        [Field/type]
            attr
        [Field/target]
            MessageViewComponent
`;
