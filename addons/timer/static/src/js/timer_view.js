odoo.define('timer.TimerView', function (require) {
    "use strict";

    const FormRender = require('web.FormRenderer');
    const FormView = require('web.FormView');
    const viewRegistry = require('web.view_registry');


    const TimerWizardRender = FormRender.extend({

        /**
         * Call `on_attach_callback` for each wizard
         *
         * @override
         */
        on_attach_callback() {
            if (!this.state.context.is_timer_pause) {
                const $btn = $('button.close');
                if ($btn.length) {
                   $btn.on('click', () => this._onClickClose());
                }
            }
            this._super(...arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * Close the wizard.
         *
         * @private
         */
        _onClickClose() {
            var context = this.state.context;
            this._rpc({
                model: context.active_model,
                method: 'action_timer_resume',
                args: [[context.active_id]],
            });
        },

    });

    const TimerWizardView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: TimerWizardRender,
        }),
    });

    viewRegistry.add('timer_wizard', TimerWizardView);

    return TimerWizardView;

});
