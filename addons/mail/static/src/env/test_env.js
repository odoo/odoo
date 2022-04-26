/** @odoo-module **/

/**
 * @param {Object} [providedEnv={}]
 * @returns {Object}
 */
export function addMessagingToEnv(providedEnv = {}) {
    const env = { ...providedEnv };
    /**
     * Environment keys used in messaging.
     */
    Object.assign(env, {
        browser: Object.assign({
            innerHeight: 1080,
            innerWidth: 1920,
            Notification: Object.assign({
                permission: 'denied',
                async requestPermission() {
                    return this.permission;
                },
            }, (env.browser && env.browser.Notification) || {}),
        }, env.browser),
    });
    return env;
}
