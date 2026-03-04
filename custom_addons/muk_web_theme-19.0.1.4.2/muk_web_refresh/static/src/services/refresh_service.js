import { registry } from '@web/core/registry';

import { getAutoLoadInterval } from '@muk_web_refresh/core/utils';

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

function makeThrottledReload(actionService) {
    let lastReloadTime = 0;
    let pendingReload = null;
    return async () => {
        const now = Date.now();
        const elapsed = now - lastReloadTime;
        if (elapsed >= getAutoLoadInterval() / 3) {
            lastReloadTime = now;
            await actionService.doAction('soft_reload');
        } else if (!pendingReload) {
            pendingReload = setTimeout(
                async () => {
                    pendingReload = null;
                    lastReloadTime = Date.now();
                    await actionService.doAction('soft_reload');
                }, 
                getAutoLoadInterval() / 3 - elapsed
            );
        }
    };
}

export const refreshService = {
    dependencies: ['bus_service', 'action'],
    start(env, { bus_service, action: actionService }) {
        const throttledReload = makeThrottledReload(actionService);
        bus_service.subscribe('muk_web_refresh.reload', (payload) => {
            if (shouldReload(actionService, payload)) {
                throttledReload();
            }
        });
        bus_service.start();
    },
};

registry.category('services').add('muk_web_refresh.reload', refreshService);
