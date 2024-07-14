/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ListController } from '@web/views/list/list_controller';

export class ResourceListController extends ListController {
    /**
     * @override
     */
    get archiveDialogProps() {
        let result = super.archiveDialogProps;
        result['body'] = _t("Archiving this resource will transform all of its future shifts into open shifts. Are you sure you want to continue?");
        return result;
    }
}
