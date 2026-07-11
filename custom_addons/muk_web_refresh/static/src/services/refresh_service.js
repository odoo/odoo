import { registry } from '@web/core/registry';

import { getAutoLoadInterval } from '@muk_web_refresh/core/utils';

export const REFRESH_VIEW_EVENT = 'muk_web_refresh.refresh-view';

/**
 * Tell whether the current view matches the reload notification payload.
 *
 * @param {object} actionService
 * @param {object} payload
 * @returns {boolean}
 */
function shouldReload(actionService, payload) {
    const controller = actionService.currentController;
    if (!controller || controller.action.type !== 'ir.actions.act_window') {
        return false;
    }
    const { model, view_types, rec_ids } = payload;
    if (controller.action.res_model !== model) {
        return false;
    }
    if (view_types?.length && !view_types.includes(controller.view?.type)) {
        return false;
    }
    if (rec_ids?.length) {
        const currentResId = controller.currentState?.resId;
        if (currentResId && !rec_ids.includes(currentResId)) {
            return false;
        }
    }
    return true;
}

/**
 * Wrap a reload callback so it fires at most once per third of the interval.
 *
 * @param {Function} reloadFn
 * @returns {Function}
 */
function makeThrottledReload(reloadFn) {
    let lastReloadTime = 0;
    let pendingReload = null;
    return async () => {
        const now = Date.now();
        const elapsed = now - lastReloadTime;
        if (elapsed >= getAutoLoadInterval() / 3) {
            lastReloadTime = now;
            await reloadFn();
        } else if (!pendingReload) {
            pendingReload = setTimeout(
                async () => {
                    pendingReload = null;
                    lastReloadTime = Date.now();
                    await reloadFn();
                },
                getAutoLoadInterval() / 3 - elapsed,
            );
        }
    };
}

export const refreshService = {
    dependencies: ['bus_service', 'action'],
    /**
     * Subscribe to reload notifications and throttle them into view refreshes.
     *
     * @param {object} env
     * @param {object} deps
     * @returns {void}
     */
    start(env, { bus_service, action: actionService }) {
        const throttledReload = makeThrottledReload(() =>
            env.bus.trigger(REFRESH_VIEW_EVENT),
        );
        bus_service.subscribe('muk_web_refresh.reload', (payload) => {
            if (shouldReload(actionService, payload)) {
                throttledReload();
            }
        });
        bus_service.start();
    },
};

registry.category('services').add('muk_web_refresh.reload', refreshService);
