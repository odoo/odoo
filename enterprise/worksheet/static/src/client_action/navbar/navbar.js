/** @odoo-module **/

import { StudioNavbar } from "@web_studio/client_action/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { resetViewCompilerCache } from "@web/views/view_compiler";

patch(StudioNavbar.prototype, {
    /**
     * @override
     */
    closeStudio() {
        const context = this.studio.editedAction && this.studio.editedAction.context;
        if (context) {
            const worksheetTemplateId = context.worksheet_template_id;
            const actionXmlId = context.action_xml_id || this.studio.editedAction.xml_id;
            if (worksheetTemplateId && actionXmlId) {
                this.actionService.doAction(actionXmlId , {
                    viewType: "form",
                    props: { resId: worksheetTemplateId },
                    stackPosition: "replacePreviousAction",
                });
                resetViewCompilerCache();
                this.env.bus.trigger("CLEAR-CACHES");
                return;
            }
        }
        super.closeStudio(...arguments);
    },
});
