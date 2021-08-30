/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            threadPreviewView
        [Field/model]
            ThreadPreviewComponent
        [Field/type]
            one
        [Field/target]
            ThreadPreviewView
        [Field/isRequired]
            true
`;
