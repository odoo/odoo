/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Dev/comment}
        Models that represent the volume chosen by the user for each partner.
    {Record/insert}
        [Record/models]
            Field
        [Field/name]
            volumeSettings
        [Field/model]
            UserSetting
        [Field/type]
            many
        [Field/target]
            VolumeSetting
        [Field/isCausal]
            true
        [Field/inverse]
            VolumeSetting/userSetting
`;
