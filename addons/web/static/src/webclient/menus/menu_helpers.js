/**
 * Traverses the given menu tree, executes the given callback for each node with
 * the node itself and the list of its ancestors as arguments.
 *
 * @param {Object} tree tree of menus as exported by the menus service
 * @param {Function} cb
 * @param {[Object]} [parents] the ancestors of the tree root, if any
 */
function traverseMenuTree(tree, cb, parents = []) {
    cb(tree, parents);
    tree.childrenTree.forEach((c) => traverseMenuTree(c, cb, parents.concat([tree])));
}

/**
 * Computes the "apps" and "menuItems" from a given menu tree.
 *
 * @param {Object} menuTree tree of menus as exported by the menus service
 * @returns {Object} with keys "apps" and "menuItems" (HomeMenu props)
 */
export function computeAppsAndMenuItems(menuTree) {
    const apps = [];
    const menuItems = [];
    traverseMenuTree(menuTree, (menuItem, parents) => {
        if (!menuItem.id || !menuItem.actionID) {
            return;
        }
        const isApp = menuItem.id === menuItem.appID;
        const item = {
            parents: parents
                .slice(1)
                .map((p) => p.name)
                .join(" / "),
            label: menuItem.name,
            id: menuItem.id,
            xmlid: menuItem.xmlid,
            actionID: menuItem.actionID,
            href: `/odoo/${menuItem.actionPath || "action-" + menuItem.actionID}`,
            appID: menuItem.appID,
        };
        if (isApp) {
            if (menuItem.webIconData) {
                item.webIconData = menuItem.webIconData;
            } else {
                const [iconClass, color, backgroundColor] = (menuItem.webIcon || "").split(",");
                if (backgroundColor !== undefined) {
                    // Could split in three parts?
                    item.webIcon = { iconClass, color, backgroundColor };
                } else {
                    item.webIconData = "/web/static/img/default_icon_app.png";
                }
            }
        } else {
            item.menuID = parents[1].id;
        }
        if (isApp) {
            apps.push(item);
        } else {
            menuItems.push(item);
        }
    });
    return { apps, menuItems };
}

/**
 * @param {Array} order
 * Sorts the apps in the homescreen menu according to the given order as an array of xmlid strings
 */
export function reorderApps(apps, order) {
    apps.sort((a, b) => {
        const aIndex = order.indexOf(a.xmlid);
        const bIndex = order.indexOf(b.xmlid);
        if (aIndex === -1 && bIndex === -1) {
            // if both items are not present, sort by original order
            return apps.indexOf(a) - apps.indexOf(b);
        }
        // not found items always before found ones
        if (aIndex === -1) {
            return -1;
        }
        if (bIndex === -1) {
            return 1;
        }
        return aIndex - bIndex; // sort by order array
    });
}
