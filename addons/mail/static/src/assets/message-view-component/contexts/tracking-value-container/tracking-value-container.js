/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Context
        [Context/name]
            trackingValueContainer
        [Context/model]
            MessageViewComponent
        [Model/fields]
            value
        [Model/template]
            trackingValueContainerForeach
                trackingValueContainer
                    trackingValue
                        trackingValueFieldName
                        trackingValueOldValue
                        trackingValueOldValueUnset
                        trackingValueSeparator
                        trackingValueNewValue
                        trackingValueNewValueUnset
`;
