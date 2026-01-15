import { EventBus } from '@odoo/owl';
import { registry } from '@web/core/registry';
import { AuthUI } from './auth_ui';

const bus = new EventBus();

export const authService = {
    start(env) {
        registry.category('main_components').add('AuthUI', { Component: AuthUI, props: { bus } });
    }
}
registry.category('services').add('auth_ui', authService);
