/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            FollowerSubtypeListComponent
        [Model/fields]
            record
        [Model/template]
            root
                content
                    header
                        title
                        closeButton
                    body
                        subtypes
                            subtypeForeach
                    footer
                        applyButton
                        cancelButton
`;
