/** @odoo-module **/

/**********************************************************************************
*
*    Copyright (c) 2017-today MuK IT GmbH.
*
*    This file is part of MuK REST for Odoo
*    (see https://mukit.at).
*
*    MuK Proprietary License v1.0
*
*    This software and associated files (the "Software") may only be used
*    (executed, modified, executed after modifications) if you have
*    purchased a valid license from MuK IT GmbH.
*
*    The above permissions are granted for a single database per purchased
*    license. Furthermore, with a valid license it is permitted to use the
*    software on other databases as long as the usage is limited to a testing
*    or development environment.
*
*    You may develop modules based on the Software or that use the Software
*    as a library (typically by depending on it, importing it and using its
*    resources), but without copying any source code or material from the
*    Software. You may distribute those modules under the license of your
*    choice, provided that this license is compatible with the terms of the
*    MuK Proprietary License (For example: LGPL, MIT, or proprietary licenses
*    similar to this one).
*
*    It is forbidden to publish, distribute, sublicense, or sell copies of
*    the Software or modified copies of the Software.
*
*    The above copyright notice and this permission notice must be included
*    in all copies or substantial portions of the Software.
*
*    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
*    OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
*    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
*    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
*    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
*    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
*    DEALINGS IN THE SOFTWARE.
*
**********************************************************************************/

import { patch } from '@web/core/utils/patch';

import { NavBar } from '@web/webclient/navbar/navbar';
import { AppsMenu } from "@muk_web_theme/webclient/appsmenu/appsmenu";
import { AppsSearch } from "@muk_web_theme/webclient/appssearch/appssearch";
import { AppsBar } from '@muk_web_theme/webclient/appsbar/appsbar';

patch(NavBar.prototype, 'muk_web_theme.NavBar', {
	getAppsMenuItems(apps) {
		return apps.map((menu) => {
			const appsMenuItem = {
				id: menu.id,
				name: menu.name,
				xmlid: menu.xmlid,
				appID: menu.appID,
				actionID: menu.actionID,
				href: this.getMenuItemHref(menu),
				action: () => this.menuService.selectMenu(menu),
			};
		    if (menu.webIconData) {
		        const prefix = (
		        	menu.webIconData.startsWith('P') ? 
	    			'data:image/svg+xml;base64,' : 
					'data:image/png;base64,'
	            );
		        appsMenuItem.webIconData = (
	    			menu.webIconData.startsWith('data:image') ? 
					menu.webIconData : 
					prefix + menu.webIconData.replace(/\s/g, '')
	            );
		    }
			return appsMenuItem;
		});
    },
});

patch(NavBar, 'muk_web_theme.NavBar', {
    components: {
        ...NavBar.components,
        AppsMenu,
        AppsSearch,
        AppsBar,
    },
});
