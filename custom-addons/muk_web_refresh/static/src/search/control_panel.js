import { useState, onWillStart, useEffect } from '@odoo/owl';

import { browser } from '@web/core/browser/browser';
import { patch } from '@web/core/utils/patch';
import { session } from '@web/session';

import {ControlPanel} from '@web/search/control_panel/control_panel';

patch(ControlPanel.prototype, {
	setup() {
		super.setup(...arguments);
        this.autoLoadState = useState({
			active: false,
			counter: 0,
        });
		onWillStart(() => {
			if (
				this.checkAutoLoadAvailability() && 
				this.getAutoLoadStorageValue()
			) {
				this.autoLoadState.active = true;
			}
		});
		useEffect(
			() => {
				if (!this.autoLoadState.active) {
					return;
				}
				this.autoLoadState.counter = (
					this.getAutoLoadRefreshInterval()
				);
				const interval = browser.setInterval(
					() => {
						this.autoLoadState.counter = (
							this.autoLoadState.counter ? 
							this.autoLoadState.counter - 1 : 
							this.getAutoLoadRefreshInterval()
						);
						if (this.autoLoadState.counter <= 0) {
							this.autoLoadState.counter = (
								this.getAutoLoadRefreshInterval()
							);
							if (this.pagerProps?.onUpdate) {
								this.pagerProps.onUpdate({
									offset: this.pagerProps.offset, 
									limit: this.pagerProps.limit
								});
							} else if (typeof this.env.searchModel?.search) {
								this.env.searchModel.search();
							}
						}
					}, 
					1000
				);
				return () => browser.clearInterval(interval);
			},
			() => [this.autoLoadState.active]
		);
	},
	checkAutoLoadAvailability() {
		return ['kanban', 'list'].includes(this.env.config.viewType);
	},
    getAutoLoadRefreshInterval() {
    	return (session.pager_autoload_interval ?? 30000) / 1000;
	},
    getAutoLoadStorageKey() {
		const keys = [
			this.env?.config?.actionId ?? '',
			this.env?.config?.viewType ?? '',
			this.env?.config?.viewId ?? '',
		];
		return `pager_autoload:${keys.join(',')}`;
    },
    getAutoLoadStorageValue() {
    	return browser.localStorage.getItem(
        	this.getAutoLoadStorageKey()
        );
	},
    setAutoLoadStorageValue() {
    	browser.localStorage.setItem(
			this.getAutoLoadStorageKey(), true
		);
	},
    removeAutoLoadStorageValue() {
    	browser.localStorage.removeItem(
            this.getAutoLoadStorageKey()
        );
	},
	toggleAutoLoad() {
		this.autoLoadState.active = (
			!this.autoLoadState.active
		);
		if (this.autoLoadState.active) {
			this.setAutoLoadStorageValue();
		} else {
			this.removeAutoLoadStorageValue();
		}
	},
});
