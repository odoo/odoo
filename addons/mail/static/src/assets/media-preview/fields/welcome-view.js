/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States the welcome view containing this media preview.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            welcomeView
        [Field/model]
            MediaPreview
        [Field/type]
            one
        [Field/target]
            WelcomeView
        [Field/isReadonly]
            true
        [Field/inverse]
            WelcomeView/mediaPreview
`;
