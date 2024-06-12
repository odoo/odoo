/** @odoo-module **/

import { registry } from "@web/core/registry";

export const appMenuService = {
    dependencies: ["menu"],
    async start(env, { menu }) {
        return {
        	getCurrentApp () {
        		return menu.getCurrentApp();
        	},
        	getAppsMenuItems() {
        		const menuItems = menu.getApps().map((item) => {
        			const appsMenuItem = {
        				id: item.id,
        				name: item.name,
        				xmlid: item.xmlid,
        				appID: item.appID,
        				actionID: item.actionID,
        				action: () => menu.selectMenu(item),
        			};
        		    if (item.webIconData) {
        		        const prefix = (
        		        	item.webIconData.startsWith('P') ? 
        	    			'data:image/svg+xml;base64,' : 
        					'data:image/png;base64,'
        	            );
        		        appsMenuItem.webIconData = (
        		        	item.webIconData.startsWith('data:image') ? 
        		        	item.webIconData : 
        					prefix + item.webIconData.replace(/\s/g, '')
        	            );
        		    }
        			const hrefParts = [`menu_id=${item.id}`];
    		        if (item.actionID) {
    		        	hrefParts.push(`action=${item.actionID}`);
    		        }
    		        appsMenuItem.href = "#" + hrefParts.join("&");
        			return appsMenuItem;
        		});
        		return menuItems;
            },
        };
    },
};

registry.category("services").add("app_menu", appMenuService);
