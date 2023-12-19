import { patch } from "@web/core/utils/patch";
import { EmployeeFormController } from "@hr/views/form_view";
import { HrPresenceCogMenu } from "../search/hr_presence_cog_menu/hr_presence_cog_menu";

patch(EmployeeFormController, {
    components: {
        ...EmployeeFormController.components,
        CogMenu: HrPresenceCogMenu,
    },
});
