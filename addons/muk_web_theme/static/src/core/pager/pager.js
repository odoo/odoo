/** @odoo-module */

/**********************************************************************************
*
*    Copyright (c) 2017-today MuK IT GmbH.
*
*    This file is part of MuK Backend Theme
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

import { useState, onWillUnmount } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { patch } from '@web/core/utils/patch';
import { session } from "@web/session";

import { Pager } from '@web/core/pager/pager';

patch(Pager.prototype, 'muk_web_theme.Pager', {
	setup() {
        this._super(...arguments);
        const autoLoad = browser.localStorage.getItem(
        	this.getAutoLoadStorageKey()
        )
        this.autoLoadInterval = false;
        this.autoLoadState = useState({
        	active: autoLoad,
        });
        if (autoLoad) {
        	this.setAutoLoad();
        }
        onWillUnmount(() => {
            this.clearAutoLoad();
        });
    },
    checkAutoLoadAvailability() {
    	return ['kanban', 'list'].includes(
    		this.env.config.viewType
    	);
    },
    getAutoLoadStorageKey() {
    	return (
    		'pager_autoload:' +
    		this.env.config.actionId + 
    		',' +
    		this.env.config.viewId
    	);
    },
    getAutoLoadIntervalTimeout() {
    	return session.pager_autoload_interval || 30000;
    },
    getAutoloadTooltip() {
    	return JSON.stringify({
    		active: this.autoLoadState.active,
    		interval: this.getAutoLoadIntervalTimeout() / 1000,
    		autoload: this.checkAutoLoadAvailability(),
    	});
    },
    setAutoLoad() {
    	this.autoLoadInterval = browser.setInterval(
	    	() => { this.navigate(0); }, 
	    	this.getAutoLoadIntervalTimeout()
    	);
    	if (this.env.config.actionId) {
    		browser.localStorage.setItem(
	            this.getAutoLoadStorageKey(), true
	        );
    	}
    },
    clearAutoLoad() {
    	if (this.autoLoadInterval) {
    		browser.clearInterval(this.autoLoadInterval);
    	}
    },
    toggleAutoLoad() {
    	this.clearAutoLoad();
    	browser.localStorage.removeItem(
            this.getAutoLoadStorageKey()
        );
    	if (this.checkAutoLoadAvailability()) {
        	this.autoLoadState.active = !this.autoLoadState.active;
        	if (this.autoLoadState.active) {
        		this.setAutoLoad();
        	}
    	}
    },
});
