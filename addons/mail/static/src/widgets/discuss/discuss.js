/** @odoo-module **/

import { DiscussContainer } from "@mail/components/discuss_container/discuss_container";

import AbstractAction from 'web.AbstractAction';

const { App } = owl;

export const DiscussWidget = AbstractAction.extend({
    template: 'mail.widgets.Discuss',
    /**
     * @override {web.AbstractAction}
     * @param {web.ActionManager} parent
     * @param {Object} action
     * @param {Object} [action.context]
     * @param {string} [action.context.active_id]
     * @param {Object} [action.params]
     * @param {string} [action.params.default_active_id]
     * @param {Object} [options={}]
     */
    init(parent, action, options={}) {
        this._super(...arguments);

        this.app = undefined;
        this.action = action;
        this.actionManager = parent;
    },
    /**
     * @override {web.AbstractAction}
     */
    destroy() {
        if (this.app) {
            this.app.destroy();
            this.app = undefined;
        }
        if (this.$buttons) {
            this.$buttons.off().remove();
        }
        this._super(...arguments);
    },
    /**
     * @override {web.AbstractAction}
     */
    async on_attach_callback() {
        this._super(...arguments);
        if (this.app) {
            // prevent twice call to on_attach_callback (FIXME)
            return;
        }

        this.app = new App(DiscussContainer, {
            templates: window.__OWL_TEMPLATES__,
            env: owl.Component.env,
            dev: owl.Component.env.isDebug(),
            translateFn: owl.Component.env._t,
            translatableAttributes: ["data-tooltip"],
            props: {
                action: this.action,
                actionManager: this.actionManager,
            },
        });
        await this.app.mount(this.el);
    },
    /**
     * @override {web.AbstractAction}
     */
    on_detach_callback() {
        this._super(...arguments);
        if (this.app) {
            this.app.destroy();
        }
        this.app = undefined;
    },
});
