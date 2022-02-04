odoo.define('website.s_countdown', function (require) {
'use strict';

const core = require('web.core');
const publicWidget = require('web.public.widget');

const qweb = core.qweb;

const CountdownWidget = publicWidget.Widget.extend({
    selector: '.s_countdown',
    xmlDependencies: ['/website/static/src/snippets/s_countdown/000.xml'],
    disabledInEditableMode: false,
    defaultColor: 'rgba(0, 0, 0, 255)',

    /**
     * @override
     */
    start: function () {
        this.$wrapper = this.$('.s_countdown_canvas_wrapper');
        this.$wrapper.addClass('d-flex justify-content-center');
        this.hereBeforeTimerEnds = false;
        this.endAction = this.el.dataset.endAction;
        this.endTime = parseInt(this.el.dataset.endTime);
        this.display = this.el.dataset.display;

        this.onlyOneUnit = this.display === 'd';

        this._update();
        this.setInterval = setInterval(this._update.bind(this), 1000);
        return this._super(...arguments);
    },
    /**
     * @override
     */
    destroy: function () {
        this.$('.s_countdown_end_redirect_message').remove();
        this.$('.s_countdown_end_message').addClass('d-none');
        this.$('span.s_countdown_text').empty();
        this.$('.s_countdown_canvas_wrapper').removeClass('d-none');

        clearInterval(this.setInterval);
        this._super(...arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Gets the time difference in seconds between now and countdown due date.
     *
     * @private
     */
    _getDelta: function () {
        const currentTimestamp = Date.now() / 1000;
        return this.endTime - currentTimestamp;
    },
    /**
     * Handles the action that should be executed once the countdown ends.
     *
     * @private
     */
    _handleEndCountdownAction: function () {
        if (this.endAction === 'redirect') {
            const redirectUrl = this.el.dataset.redirectUrl || '/';
            if (this.hereBeforeTimerEnds) {
                // Wait a bit, if the landing page has the same publish date
                setTimeout(() => window.location = redirectUrl, 500);
            } else {
                // Show (non editable) msg when user lands on already finished countdown
                if (!this.$('.s_countdown_end_redirect_message').length) {
                    const $container = this.$('> .container, > .container-fluid, > .o_container_small');
                    $container.append(
                        $(qweb.render('website.s_countdown.end_redirect_message', {
                            redirectUrl: redirectUrl,
                        }))
                    );
                }
            }
        } else if (this.endAction === 'message' || this.endAction === 'message_no_countdown') {
            this.$('.s_countdown_end_message').removeClass('d-none');
        }
    },
    /**
     * Updates the remaining time shown by the countdown.
     *
     * @private
     */
    _update: function () {
        let timeDelta = this._getDelta();
        let data = [];

        for (const unit of this.display) {
            const period = {'d': 86400, 'h': 3600, 'm': 60, 's': 1}[unit];
            data.push(Math.floor(timeDelta / period));
            timeDelta %= period;
        }

        this.isFinished = timeDelta < 0;
        const hideCountdown = this.isFinished && !this.editableMode && this.$el.hasClass('hide-countdown');
        const counterSelector = 'text[y="50"], span.o_not_editable';
        this.$wrapper[0].querySelectorAll(counterSelector).forEach((el, i) => {
            el.textContent = data[i];
        });
        this.$wrapper[0].querySelectorAll('[pathLength]').forEach((el, i) => {
            const max = parseInt(el.getAttribute('pathLength'));
            el.setAttribute('stroke-dasharray', `${data[i]} ${max - data[i]}`);
        });

        if (this.isFinished) {
            const $container = this.$('> .container, > .container-fluid, > .o_container_small');
            clearInterval(this.setInterval);
            $container.toggleClass('d-none', hideCountdown);
            if (!this.editableMode) {
                this._handleEndCountdownAction();
            }
        }
    },
});

publicWidget.registry.countdown = CountdownWidget;

return CountdownWidget;
});
