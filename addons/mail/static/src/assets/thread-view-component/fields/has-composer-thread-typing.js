/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        If set, determines whether the composer should display status of
        members typing on related thread. When this prop is not provided,
        it defaults to composer component default value.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            hasComposerThreadTyping
        [Field/model]
            ThreadViewComponent
        [Field/type]
            attr
        [Field/target]
            Boolean
`;
