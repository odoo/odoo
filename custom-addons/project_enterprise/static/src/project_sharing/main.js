/** @odoo-module  **/

import { hasTouch } from "@web/core/browser/feature_detection";
import { startWebClient } from '@web/start';
import { ProjectSharingWebClient } from '@project/project_sharing/project_sharing';
import { removeServices } from './remove_services';

removeServices();
(async () => {
    await startWebClient(ProjectSharingWebClient);
    document.body.classList.toggle("o_touch_device", hasTouch());
})();
