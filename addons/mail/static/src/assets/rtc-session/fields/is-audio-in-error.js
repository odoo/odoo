/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        States whether there is currently an error with the audio element.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            isAudioInError
        [Field/model]
            RtcSession
        [Field/type]
            attr
        [Field/target]
            Boolean
        [Field/default]
            false
`;
