/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            welcomeView
        [Field/model]
            WelcomeViewComponent
        [Field/type]
            one
        [Field/target]
            WelcomeView
        [Field/isRequired]
            true
`;
