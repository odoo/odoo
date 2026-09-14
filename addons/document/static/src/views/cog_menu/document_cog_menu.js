/** @odoo-module native */
import { registry } from "@web/core/registry";
import { CogMenu } from "@web/search/cog_menu/cog_menu";
import { COG_MENU_REGISTRY_VALIDATION } from "@web/search/cog_menu/cog_menu_group";
import { getDisplayedRegistryItems } from "@web/search/utils/misc";
import { documentsCogMenuItemArchive } from "./document_cog_menu_item_archive.js";
import { documentCogMenuPinAction } from "./document_cog_menu_pin_actions.js";
import { documentsCogMenuItemDetails } from "./document_cog_menu_item_details.js";
import { documentsCogMenuItemDownload } from "./document_cog_menu_item_download.js";
import { documentsCogMenuItemShare } from "./document_cog_menu_item_share.js";
import { documentsCogMenuItemRename } from "./document_cog_menu_item_rename.js";
import { documentsCogMenuItemShortcut } from "./document_cog_menu_item_shortcut.js";
import {
    documentsCogMenuItemStarAdd,
    documentsCogMenuItemStarRemove,
} from "./document_cog_menu_item_star.js";
import { documentsCogMenuItemAutomations } from "./document_cog_menu_item_automations.js";

export const documentsCogMenuRegistry = registry.category("documents_cog_menu");

documentsCogMenuRegistry.addValidation(COG_MENU_REGISTRY_VALIDATION);

for (const [key, item] of [
    ["download", documentsCogMenuItemDownload],
    ["rename", documentsCogMenuItemRename],
    ["share", documentsCogMenuItemShare],
    ["shortcut", documentsCogMenuItemShortcut],
    ["star-add", documentsCogMenuItemStarAdd],
    ["star-remove", documentsCogMenuItemStarRemove],
    ["details", documentsCogMenuItemDetails],
    ["trash", documentsCogMenuItemArchive],
    ["pin-actions", documentCogMenuPinAction],
    ["automations", documentsCogMenuItemAutomations],
]) {
    documentsCogMenuRegistry.add(key, item);
}

export class DocumentsCogMenu extends CogMenu {
    async _registryItems() {
        const [globalItems, documentsItems] = await Promise.all([
            super._registryItems(),
            getDisplayedRegistryItems(documentsCogMenuRegistry, this.env),
        ]);
        return [
            ...globalItems,
            ...documentsItems.map((item) => ({
                ...item,
                key: `documents-${item.key}`,
            })),
        ];
    }
}
