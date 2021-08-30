/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            composerView
        [Field/model]
            ComposerViewComponent
        [Field/type]
            one
        [Field/target]
            ComposerView
        [Field/isRequired]
            true
`;
