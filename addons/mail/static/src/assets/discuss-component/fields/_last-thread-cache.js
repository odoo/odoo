/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Locally tracked store props 'activeThreadCache'.
        Useful to set scroll position from last stored one and to display
        rainbox man on inbox.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            _lastThreadCache
        [Field/model]
            DiscussComponent
        [Field/type]
            attr
        [Field/target]
            String
`;
