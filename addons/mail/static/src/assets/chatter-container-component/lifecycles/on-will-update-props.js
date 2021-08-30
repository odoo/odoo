/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Lifecycle
        [Lifecycle/name]
            onWillUpdateProps
        [Lifecycle/model]
            ChatterContainerComponent
        [Lifecycle/behavior]
            {ChatterContainerComponent/_insertFromProps}
                @record
                @nextProps
`;
