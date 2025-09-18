// @ts-check

/** @module @web/views/form/form_cog_menu/form_cog_menu - Form-view variant of the cog menu with save-before-action behavior */

/** Form-view variant of the cog menu, adding save-before-action behavior. */
import { CogMenu } from "@web/search/cog_menu/cog_menu";
export class FormCogMenu extends CogMenu {
    static template = "web.FormCogMenu";
}
