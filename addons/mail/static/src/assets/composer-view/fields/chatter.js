/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the chatter which this composer allows editing (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            chatter
        [Field/model]
            ComposerView
        [Field/type]
            one
        [Field/target]
            Chatter
        [Field/isReadonly]
            true
        [Field/inverse]
            Chatter/composerView
`;
