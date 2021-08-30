/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the message view on which this composer allows editing (if any).
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            messageViewInEditing
        [Field/model]
            ComposerView
        [Field/type]
            one
        [Field/target]
            MessageView
        [Field/isReadonly]
            true
        [Field/inverse]
            MessageView/composerViewInEditing
`;
