/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            VolumeSetting
        [Model/fields]
            guest
            id
            partner
            userSetting
            volume
        [Model/id]
            VolumeSetting/id
        [Model/onChanges]
            VolumeSetting/_onChangeVolume
`;
