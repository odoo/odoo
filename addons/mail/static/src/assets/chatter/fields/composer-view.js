/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Determines the composer view used to post in this chatter (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            composerView
        [Field/model]
            Chatter
        [Field/type]
            one
        [Field/target]
            ComposerView
        [Field/isCausal]
            true
        [Field/inverse]
            ComposerView/chatter
`;
