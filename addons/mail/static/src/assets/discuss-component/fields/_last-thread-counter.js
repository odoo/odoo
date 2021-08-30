/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Locally tracked store props 'threadCounter'.
        Useful to display the rainbow man on inbox.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _lastThreadCounter
        [Field/model]
            DiscussComponent
        [Field/type]
            attr
        [Field/target]
            Number
`;
