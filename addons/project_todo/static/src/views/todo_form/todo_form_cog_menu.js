import { FormCogMenu } from "@web/views/form/form_cog_menu/form_cog_menu";

export class TodoFormCogMenu extends FormCogMenu {
    async _registryItems() {
        // we don't want action added by other apps since the todo form view is more personal task
        return [];
    }
}
