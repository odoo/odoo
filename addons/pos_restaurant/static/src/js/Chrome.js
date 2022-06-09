odoo.define('pos_restaurant.chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');

    const NON_IDLE_EVENTS = 'mousemove mousedown touchstart touchend touchmove click scroll keypress'.split(/\s+/);
    let IDLE_TIMER_SETTER;

    const PosResChrome = (Chrome) =>
        class extends Chrome {
            /**
             * @override
             */
            async start() {
                await super.start();
                if (this.env.pos.config.iface_floorplan) {
                    this._setActivityListeners();
                }
            }
            /**
             * @override
             * Do not set `FloorScreen` to the order.
             */
            _setScreenData(name) {
                if (name === 'FloorScreen') return;
                super._setScreenData(...arguments);
            }
            /**
             * @override
             * `FloorScreen` is the start screen if there are floors.
             */
            get startScreen() {
                if (this.env.pos.config.iface_floorplan) {
                    const table = this.env.pos.table;
                    return { name: 'FloorScreen', props: { floor: table ? table.floor : null } };
                } else {
                    return super.startScreen;
                }
            }
            /**
             * @override
             * Order is set to null when table is selected. There is no saved
             * screen for null order so show `FloorScreen` instead.
             */
            _showSavedScreen(pos, newSelectedOrder) {
                if (!newSelectedOrder) {
                    this.showScreen('FloorScreen', { floor: pos.table ? pos.table.floor : null });
                } else {
                    super._showSavedScreen(pos, newSelectedOrder);
                }
            }
            _setActivityListeners() {
                IDLE_TIMER_SETTER = this._setIdleTimer.bind(this);
                for (const event of NON_IDLE_EVENTS) {
                    window.addEventListener(event, IDLE_TIMER_SETTER);
                }
            }
            _setIdleTimer() {
                if (this._shouldResetIdleTimer()) {
                    clearTimeout(this.idleTimer);
                    this.idleTimer = setTimeout(() => {
                        this._actionAfterIdle();
                    }, 60000);
                }
            }
            _actionAfterIdle() {
                // We also need to check if the action still need to be triggered
                if (!this._shouldResetIdleTimer()) {
                    return;
                }
                if (this.tempScreen.isShown) {
                    this.trigger('close-temp-screen');
                }
                const table = this.env.pos.table;
                this.showScreen('FloorScreen', { floor: table ? table.floor : null });
            }
            _shouldResetIdleTimer() {
                return super._shouldResetIdleTimer() && this.env.pos.config.iface_floorplan && this.mainScreen.name !== 'FloorScreen';
            }
            __showScreen() {
                super.__showScreen(...arguments);
                this._setIdleTimer();
            }
            /**
             * @override
             * Before closing pos, we remove the event listeners set on window
             * for detecting activities outside FloorScreen.
             */
            async _closePos() {
                if (IDLE_TIMER_SETTER) {
                    for (const event of NON_IDLE_EVENTS) {
                        window.removeEventListener(event, IDLE_TIMER_SETTER);
                    }
                }
                await super._closePos();
            }
        };

    Registries.Component.extend(Chrome, PosResChrome);

    return Chrome;
});
