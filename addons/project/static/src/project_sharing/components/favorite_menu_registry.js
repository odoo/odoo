/** @odoo-module **/

import FavoriteMenuLegacy from 'web.FavoriteMenu';
import CustomFavoriteItemLegacy from 'web.CustomFavoriteItem';
import { registry } from "@web/core/registry";


/**
 * Remove all components contained in the favorite menu registry except the CustomFavoriteItem
 * component for only the project sharing feature.
 */
export function prepareFavoriteMenuRegister() {
    let customFavoriteItemKey = 'favorite-generator-menu';
    const keys = FavoriteMenuLegacy.registry.keys().filter(key => key !== customFavoriteItemKey);
    FavoriteMenuLegacy.registry = Object.assign(FavoriteMenuLegacy.registry, {
        map: {},
        _scoreMapping: {},
        _sortedKeys: null,
    });
    FavoriteMenuLegacy.registry.add(customFavoriteItemKey, CustomFavoriteItemLegacy, 0);
    // notify the listeners, we keep only one key in this registry.
    for (const key of keys) {
        for (const callback of FavoriteMenuLegacy.registry.listeners) {
            callback(key, undefined);
        }
    }

    customFavoriteItemKey = 'custom-favorite-item';
    const favoriteMenuRegistry = registry.category("favoriteMenu");
    for (const [key] of favoriteMenuRegistry.getEntries()) {
        if (key !== customFavoriteItemKey) {
            favoriteMenuRegistry.remove(key);
        }
    }
}
