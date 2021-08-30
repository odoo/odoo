/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isComposerFocused
        [Field/model]
            ThreadView
        [Field/type]
            attr
        [Field/related]
            ThreadView/composerView
            ComposerView/isFocused
`;
