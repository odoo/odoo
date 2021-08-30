/** @odoo-module **/

import { Define } from '@mail/define';

export default Define`
    {Record/insert}
        [Record/models]
            Model
        [Model/name]
            DialogManagerComponent
        [Model/actions]
            DialogManagerComponent/_checkDialogOpen
        [Model/template]
            root
                dialogForeach
        [Model/lifecycles]
            onUpdate
`;
