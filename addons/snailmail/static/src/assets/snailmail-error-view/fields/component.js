/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            component
        [Field/model]
            SnailmailErrorView
        [Field/type]
            attr
        [Field/target]
            SnailmailErrorComponent
`;
