import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { documentsCogMenuItemArchive } from "./documents_cog_menu_item_archive";
import { documentCogMenuPinAction } from "./documents_cog_menu_pin_actions";
import { documentsCogMenuItemDetails } from "./documents_cog_menu_item_details";
import { documentsCogMenuItemDownload } from "./documents_cog_menu_item_download";
import { documentsCogMenuItemShare } from "./documents_cog_menu_item_share";
import { documentsCogMenuItemRename } from "./documents_cog_menu_item_rename";
import { documentsCogMenuItemShortcut } from "./documents_cog_menu_item_shortcut";
import {
    documentsCogMenuItemStarAdd,
    documentsCogMenuItemStarRemove,
} from "./documents_cog_menu_item_star";
import { documentsCogMenuItemAutomations } from "./documents_cog_menu_item_automations";

const documentMenuItems = [
    documentsCogMenuItemDownload,
    documentsCogMenuItemRename,
    documentsCogMenuItemShare,
    documentsCogMenuItemShortcut,
    documentsCogMenuItemStarAdd,
    documentsCogMenuItemStarRemove,
    documentsCogMenuItemDetails,
    documentsCogMenuItemArchive,
    documentCogMenuPinAction,
    documentsCogMenuItemAutomations,
];

/**
 * Temporary override to only show the menu entries that are working on Document
 * (ex.: "spreadsheet-cog-menu" is currently not working).
 */
export class DocumentsCogMenu extends CogMenu {
    async _registryItems() {
        const enabledItems = [];
        for (const item of documentMenuItems) {
            if (await item.isDisplayed(this.env)) {
                enabledItems.push({
                    Component: item.Component,
                    groupNumber: item.groupNumber,
                    key: item.Component.name,
                });
            }
        }
        return enabledItems;
    }
}
