import { browser } from '@web/core/browser/browser';
import { useBus } from '@web/core/utils/hooks';
import { patch } from '@web/core/utils/patch';

import { ControlPanel } from '@web/search/control_panel/control_panel';

import { getAutoLoadInterval } from '@muk_web_refresh/core/utils';
import { REFRESH_VIEW_EVENT } from '@muk_web_refresh/services/refresh_service';

import { useState, onWillDestroy, useEffect, useExternalListener } from '@odoo/owl';

/**
 * Provide a callback that briefly flashes the refresh animation on the content.
 *
 * @param {number} timeout
 * @returns {Function}
 */
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

/**
 * Extend the control panel with a manual refresh button and a per-view
 * auto-load timer toggled by double-clicking the refresh action.
 */
patch(ControlPanel.prototype, {
    setup() {
        super.setup();
        this._clickTimeout = null;
        this.refreshAnimation = useRefreshAnimation(600);
        useBus(this.env.bus, REFRESH_VIEW_EVENT, () => {
            this.refreshView();
        });
        this.autoLoadState = useState({
            active:
                this.checkAutoLoadAvailability() && !!this.getAutoLoadStorageValue(),
            counter: 0,
        });
        this._refreshInFlight = false;
        this.visibilityState = useState({
            hidden: document.hidden,
        });
        useExternalListener(document, 'visibilitychange', () => {
            this.visibilityState.hidden = document.hidden;
        });
        onWillDestroy(() => {
            if (this._clickTimeout) {
                clearTimeout(this._clickTimeout);
            }
        });
        useEffect(
            () => {
                if (!this.autoLoadState.active || this.visibilityState.hidden) {
                    return;
                }
                this.autoLoadState.counter = this.getAutoLoadRefreshInterval();
                const interval = browser.setInterval(() => {
                    this.autoLoadState.counter = this.autoLoadState.counter
                        ? this.autoLoadState.counter - 1
                        : this.getAutoLoadRefreshInterval();
                    if (this.autoLoadState.counter <= 0) {
                        this.autoLoadState.counter = this.getAutoLoadRefreshInterval();
                        if (!this._refreshInFlight) {
                            this._refreshInFlight = true;
                            this.refreshView().finally(() => {
                                this._refreshInFlight = false;
                            });
                        }
                    }
                }, 1000);
                return () => browser.clearInterval(interval);
            },
            () => [this.autoLoadState.active, this.visibilityState.hidden],
        );
    },
    checkAutoLoadAvailability() {
        return ['kanban', 'list'].includes(this.env.config.viewType);
    },
    checkRefreshAvailability() {
        return !['base_settings'].includes(this.env.config.viewSubType);
    },
    getAutoLoadRefreshInterval() {
        return getAutoLoadInterval() / 1000;
    },
    /**
     * Build the per-action localStorage key tracking the auto-load toggle.
     *
     * @returns {string}
     */
    getAutoLoadStorageKey() {
        const keys = [
            this.env?.config?.actionId ?? '',
            this.env?.config?.viewType ?? '',
            this.env?.config?.viewId ?? '',
        ];
        return `pager_autoload:${keys.join(',')}`;
    },
    getAutoLoadStorageValue() {
        return browser.localStorage.getItem(this.getAutoLoadStorageKey());
    },
    setAutoLoadStorageValue() {
        browser.localStorage.setItem(this.getAutoLoadStorageKey(), true);
    },
    removeAutoLoadStorageValue() {
        browser.localStorage.removeItem(this.getAutoLoadStorageKey());
    },
    toggleAutoLoad() {
        this.autoLoadState.active = !this.autoLoadState.active;
        if (this.autoLoadState.active) {
            this.setAutoLoadStorageValue();
        } else {
            this.removeAutoLoadStorageValue();
        }
    },
    /**
     * Reload the current view through the pager or the search model.
     *
     * @returns {Promise<boolean>}
     */
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
        this._clickTimeout = setTimeout(async () => {
            this._clickTimeout = null;
            if (await this.refreshView()) {
                this.refreshAnimation();
            }
        }, 300);
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
