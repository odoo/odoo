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

import { Component, useState, useExternalListener } from "@odoo/owl";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { useAutofocus, useService } from '@web/core/utils/hooks';
import { useHotkey } from '@web/core/hotkeys/hotkey_hook';
import { fuzzyLookup } from '@web/core/utils/search';
import { debounce } from '@web/core/utils/timing';

export class AppsSearch extends Component {
	setup() {
    	super.setup();
        this.searchInput = useAutofocus();
    	this.state = useState({
            hasResults: false,
            results: [],
        });
        this.menuService = useService('menu');
		Object.assign(this, computeAppsAndMenuItems(
			this.menuService.getMenuAsTree('root')
		));
    	this._onInput = debounce(this._onInput, 100);
    }
	_onInput() {
		const query = this.searchInput.el.value;
        if (query !== '') {
            const results = [];
            fuzzyLookup(
        		query, this.apps, (menu) => {
        			return menu.label
        		}
            ).forEach((menu) => {
	            const result = {
	        		id: menu.id,
					name: menu.label,
					xmlid: menu.xmlid,
					appID: menu.appID,
					actionID: menu.actionID,
					action: () => this.menuService.selectMenu(menu),
	        		href: menu.href || `#menu_id=${menu.id}&amp;action_id=${menu.actionID}`,
	            };
	            if (menu.webIconData) {
	                const prefix = (
			        	menu.webIconData.startsWith('P') ? 
		    			'data:image/svg+xml;base64,' : 
						'data:image/png;base64,'
		            );
	                result.webIconData = (
		    			menu.webIconData.startsWith('data:image') ? 
						menu.webIconData : 
						prefix + menu.webIconData.replace(/\s/g, '')
		            );
	                result.style = `background-image:url("${result.webIconData}");`
	            }
	            results.push(result);
	        });
            fuzzyLookup(
            	query, this.menuItems, (menu) => {
	                return `${menu.parents} / ${menu.label}`.split('/').reverse().join('/')
	            }
            ).forEach((menu) => {
            	results.push({
	        		id: menu.id,
                    name: `${menu.parents} / ${menu.label}`,
					xmlid: menu.xmlid,
					appID: menu.appID,
					actionID: menu.actionID,
					action: () => this.menuService.selectMenu(menu),
                    href: menu.href || `#menu_id=${menu.id}&amp;action_id=${menu.actionID}`,
                });
            });
        	this.state.results = results;
            this.state.hasResults = true;
        } else {
        	this.state.results = [];
        	this.state.hasResults = false;
        }
    }
    _onKeyDown(ev) {
        if (ev.code === 'Escape') {
            ev.stopPropagation();
            ev.preventDefault();
            if (this.searchInput.el.value) {
                this.state.results = [];
                this.state.hasResults = false;
                this.searchInput.el.value = '';
            } else {
                this.env.bus.trigger('ACTION_MANAGER:UI-UPDATED');
            }
        }
    }
}

Object.assign(AppsSearch, {
    template: 'muk_web_theme.AppsSearch',
});

