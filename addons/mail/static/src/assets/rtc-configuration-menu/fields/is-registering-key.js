/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        true if listening to keyboard input to register the push to talk key.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isRegisteringKey
        [Field/model]
            RtcConfigurationMenu
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
