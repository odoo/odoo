/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        true if the viewer is in a compact format, like in a chat window.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            compact
        [Field/model]
            ThreadViewer
        [Field/related]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
