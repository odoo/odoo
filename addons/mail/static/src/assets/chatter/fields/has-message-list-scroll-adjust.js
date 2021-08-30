/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Whether the message list should manage its scroll.
        In particular, when the chatter is on the form view's side,
        then the scroll is managed by the message list.
        Also, the message list shoud not manage the scroll if it shares it
        with the rest of the page.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasMessageListScrollAdjust
        [Field/model]
            Chatter
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
