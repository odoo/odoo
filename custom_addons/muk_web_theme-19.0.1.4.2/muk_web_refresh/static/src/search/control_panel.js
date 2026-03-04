import { browser } from '@web/core/browser/browser';
import { patch } from '@web/core/utils/patch';

import { ControlPanel } from '@web/search/control_panel/control_panel';

import { getAutoLoadInterval } from '@muk_web_refresh/core/utils';

import { useState, onWillDestroy, useEffect } from '@odoo/owl';

function useRefreshAnimation(timeout) {
    let timeoutId = null;

    function contentClassList() {
        const content = document.querySelector('.o_content');
        return content ? content.classList : null;
    }

    function clearAnimationTimeout() {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = null;
    }

    function animate() {
        clearAnimationTimeout();
        const classList = contentClassList();
        if (classList) {
            classList.add('mk_refresh');
            timeoutId = setTimeout(() => {
                classList.remove('mk_refresh');
                clearAnimationTimeout();
            }, timeout);
        }
    }

    return animate;
}

patch(ControlPanel.prototype, {
    setup() {
        super.setup();
        this._clickTimeout = null;
        this.refreshAnimation = useRefreshAnimation(600);
        this.autoLoadState = useState({
            active: (
                this.checkAutoLoadAvailability() &&
                !!this.getAutoLoadStorageValue()
            ),
            counter: 0,
        });
        onWillDestroy(() => {
            if (this._clickTimeout) {
                clearTimeout(this._clickTimeout);
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
                            this.refreshView();
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
        return ['kanban', 'list'].includes(
            this.env.config.viewType
        );
    },
    checkRefreshAvailability() {
        return !['base_settings'].includes(
            this.env.config.viewSubType
        );
    },
    getAutoLoadRefreshInterval() {
        return getAutoLoadInterval() / 1000;
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
    async refreshView() {
        if (this.pagerProps?.onUpdate) {
            await this.pagerProps.onUpdate({
                offset: this.pagerProps.offset,
                limit: this.pagerProps.limit,
            });
            return true;
        }
        if (typeof this.env.searchModel?.search === 'function') {
            this.env.searchModel.search();
            return true;
        }
        return false;
    },
    onClickRefresh() {
        if (this._clickTimeout) {
            clearTimeout(this._clickTimeout);
            this._clickTimeout = null;
        }
        this._clickTimeout = setTimeout(
            async () => {
                this._clickTimeout = null;
                if (await this.refreshView()) {
                    this.refreshAnimation();
                }
            }, 
            300
        );
    },
    onDblClickRefresh() {
        if (this._clickTimeout) {
            clearTimeout(this._clickTimeout);
            this._clickTimeout = null;
        }
        if (this.checkAutoLoadAvailability()) {
            this.toggleAutoLoad();
        }
    },
});
