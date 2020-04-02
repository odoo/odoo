odoo.define('point_of_sale.chrome', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const { debounce } = owl.utils;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { useListener } = require('web.custom_hooks');
    const { CrashManager } = require('web.CrashManager');
    const { BarcodeEvents } = require('barcodes.BarcodeEvents');
    const { NumberBuffer } = require('point_of_sale.NumberBuffer');
    const { loadCSS } = require('web.ajax');
    const Registry = require('point_of_sale.ComponentsRegistry');

    // This is kind of a trick.
    // We get a reference to the whole exports so that
    // when we create an instance of one of the classes,
    // we instantiate the extended one.
    const models = require('point_of_sale.models');

    /**
     * Chrome is the root component of the PoS App.
     */
    class Chrome extends PosComponent {
        static template = 'Chrome';
        constructor() {
            super(...arguments);
            useListener('show-main-screen', this.__showScreen);
            useListener('pos-error', this.onPosError);
            useListener('toggle-debug-widget', debounce(this._toggleDebugWidget, 100));
            useListener('show-popup', this.__showPopup);
            useListener('close-popup', this.__closePopup);
            useListener('show-temp-screen', this.__showTempScreen);
            useListener('close-temp-screen', this.__closeTempScreen);
            useListener('close-pos', this._closePos);
            useListener('loading-skip-callback', () => this._loadingSkipCallback());
            useListener('set-selected-category-id', this._setSelectedCategoryId);
            NumberBuffer.activate();

            this.state = useState({
                uiState: 'LOADING', // 'LOADING' | 'READY' | 'CLOSING'
                debugWidgetIsShown: true,
                hasBigScrollBars: false,
                selectedCategoryId: { value: 0 },
            });

            this.loading = useState({
                message: 'Loading',
                skipButtonIsShown: false,
            });

            this.mainScreen = useState({ name: null, component: null });
            this.mainScreenProps = {};

            this.popup = useState({ isShown: false, name: null, component: null });
            this.popupProps = {}; // We want to avoid making the props to become Proxy!

            this.tempScreen = useState({ isShown: false, name: null, component: null });
            this.tempScreenProps = {};

            this.progressbar = useRef('progressbar');

            this.previous_touch_y_coordinate = -1;
        }

        // OVERLOADED METHODS //

        mounted() {
            // remove default webclient handlers that induce click delay
            $(document).off();
            $(window).off();
            $('html').off();
            $('body').off();
            // The above lines removed the bindings, but we really need them for the barcode
            BarcodeEvents.start();
        }
        willUnmount() {
            BarcodeEvents.stop();
        }
        destroy() {
            super.destroy(...arguments);
            this.env.pos.destroy();
        }
        catchError(error) {
            console.error(error);
        }

        // GETTERS //

        get clientScreenButtonIsShown() {
            return (
                this.env.pos.config.use_proxy && this.env.pos.config.iface_customer_facing_display
            );
        }
        /**
         * Startup screen can be based on pos config so the startup screen
         * is only determined after pos data is completely loaded.
         *
         * NOTE: Wait for pos data to be completed before calling this getter.
         */
        get startScreen() {
            if (this.state.uiState !== 'READY') {
                console.warn(
                    `Accessing startScreen of Chrome component before 'state.uiState' to be 'READY' is not recommended.`
                );
            }
            return { name: 'ProductScreen' };
        }

        // CONTROL METHODS //

        /**
         * Call this function after the Chrome component is mounted.
         * This will load pos and assign it to the environment.
         */
        async start() {
            try {
                // Instead of passing chrome to the instantiation the PosModel,
                // we inject functions needed by pos.
                // This way, we somehow decoupled Chrome from PosModel.
                // We can then test PosModel independently from Chrome by supplying
                // mocked version of these default attributes.
                const posModelDefaultAttributes = {
                    rpc: this.rpc.bind(this),
                    session: this.env.session,
                    do_action: this.props.webClient.do_action.bind(this.props.webClient),
                    setLoadingMessage: this.setLoadingMessage.bind(this),
                    showLoadingSkip: this.showLoadingSkip.bind(this),
                    setLoadingProgress: this.setLoadingProgress.bind(this),
                };
                this.env.pos = new models.PosModel(posModelDefaultAttributes);
                await this.env.pos.ready;
                this._buildChrome();
                this.state.selectedCategoryId.value = this.env.pos.config.iface_start_categ_id
                    ? this.env.pos.config.iface_start_categ_id[0]
                    : 0;
                this.state.uiState = 'READY';
                this.env.pos.on('change:selectedOrder', this._showSavedScreen, this);
                this._showStartScreen();
                this.env.pos.push_orders(); // push order in the background, no need to await
            } catch (error) {
                let title = 'Unknown Error',
                    body;

                if (error.message && [100, 200, 404, -32098].includes(error.message.code)) {
                    // this is the signature of rpc error
                    if (error.message.code === -32098) {
                        title = 'Network Failure (XmlHttpRequestError)';
                        body =
                            'The Point of Sale could not be loaded due to a network problem.\n' +
                            'Please check your internet connection.';
                    } else if (error.message.code === 200) {
                        title = error.message.data.message || this.env._t('Server Error');
                        body =
                            error.message.data.debug ||
                            this.env._t(
                                'The server encountered an error while receiving your order.'
                            );
                    }
                } else if (error instanceof Error) {
                    title = error.message;
                    body = error.stack;
                }

                await this.showPopup('ErrorTracebackPopup', {
                    title,
                    body,
                    exitButtonIsShown: true,
                });
            }
        }

        // EVENT HANDLERS //

        _showStartScreen() {
            const { name, props } = this.startScreen;
            this.showScreen(name, props);
        }
        /**
         * Show the screen saved in the order when the `selectedOrder` of pos is changed.
         * @param {models.PosModel} pos
         * @param {models.Order} newSelectedOrder
         */
        _showSavedScreen(pos, newSelectedOrder) {
            const { name, props } = this._getSavedScreen(newSelectedOrder);
            this.showScreen(name, props);
        }
        _getSavedScreen(order) {
            return order.get_screen_data('screen') || { name: 'ProductScreen' };
        }
        _setSelectedCategoryId(event) {
            this.state.selectedCategoryId.value = event.detail;
        }
        __showPopup(event) {
            const { name, props, resolve } = event.detail;
            const popupConstructor = this.constructor.components[name];
            if (popupConstructor.dontShow) {
                resolve();
                return;
            }
            this.popup.isShown = true;
            this.popup.name = name;
            this.popup.component = popupConstructor;
            this.popupProps = { ...props, resolve };
        }
        __closePopup() {
            this.popup.isShown = false;
        }
        __showTempScreen(event) {
            const { name, props, resolve } = event.detail;
            this.tempScreen.isShown = true;
            this.tempScreen.name = name;
            this.tempScreen.component = this.constructor.components[name];
            this.tempScreenProps = { ...props, resolve };
        }
        __closeTempScreen() {
            this.tempScreen.isShown = false;
        }
        __showScreen({ detail: { name, props } }) {
            // 1. Set the information of the screen to display.
            this.mainScreen.name = name;
            this.mainScreen.component = this.constructor.components[name];
            this.mainScreenProps = {
                selectedCategoryId: this.state.selectedCategoryId,
                ...(props || {}),
            };
            // 2. Save the screen to the order.
            //  - This screen is shown when the order is selected.
            this._setScreenData(name, props);
        }
        /**
         * Set the latest screen to the current order. This is done so that
         * when the order is selected again, the ui returns to the latest screen
         * saved in the order.
         *
         * @param {string} name Screen name
         * @param {Object} props props for the Screen component
         */
        _setScreenData(name, props) {
            const order = this.env.pos.get_order();
            if (order) {
                order.set_screen_data('screen', { name, props });
            }
        }
        async _closePos() {
            // If pos is not properly loaded, we just go back to /web without
            // doing anything in the order data.
            if (!this.env.pos) {
                window.location = '/web#action=point_of_sale.action_client_pos_menu';
            }

            this.state.uiState = 'CLOSING';
            this.loading.skipButtonIsShown = false;
            this.setLoadingMessage(this.env._t('Closing ...'));

            if (this.env.pos.db.get_orders().length) {
                // If there are orders in the db left unsynced, we try to sync them.
                try {
                    await this.env.pos.push_orders();
                } catch (error) {
                    console.warn(error);
                }
                const reason = this.env.pos.get('failed')
                    ? this.env._t(
                          'Some orders could not be submitted to ' +
                              'the server due to configuration errors. ' +
                              'You can exit the Point of Sale, but do ' +
                              'not close the session before the issue ' +
                              'has been resolved.'
                      )
                    : this.env._t(
                          'Some orders could not be submitted to ' +
                              'the server due to internet connection issues. ' +
                              'You can exit the Point of Sale, but do ' +
                              'not close the session before the issue ' +
                              'has been resolved.'
                      );
                const { confirmed } = await this.showPopup('ConfirmPopup', {
                    title: this.env._t('Offline Orders'),
                    body: reason,
                });
                if (confirmed) {
                    window.location = '/web#action=point_of_sale.action_client_pos_menu';
                } else {
                    this.state.uiState = 'READY';
                }
            } else {
                window.location = '/web#action=point_of_sale.action_client_pos_menu';
            }
        }
        _toggleDebugWidget() {
            this.state.debugWidgetIsShown = !this.state.debugWidgetIsShown;
        }
        onPosError(event) {
            console.warn(event.detail.error);
        }

        // TO PASS AS PARAMETERS //

        setLoadingProgress(fac) {
            if (this.progressbar.el) {
                this.progressbar.el.style.width = `${Math.floor(fac * 100)}%`;
            }
        }
        setLoadingMessage(msg, progress) {
            this.loading.message = msg;
            if (typeof progress !== 'undefined') {
                this.setLoadingProgress(progress);
            }
        }
        /**
         * Show Skip button in the loading screen and allow to assign callback
         * when the button is pressed.
         *
         * @param {Function} callback function to call when Skip button is pressed.
         */
        showLoadingSkip(callback) {
            if (callback) {
                this.loading.skipButtonIsShown = true;
                this._loadingSkipCallback = callback;
            }
        }

        // MISC METHODS //

        _buildChrome() {
            if ($.browser.chrome) {
                var chrome_version = $.browser.version.split('.')[0];
                if (parseInt(chrome_version, 10) >= 50) {
                    loadCSS('/point_of_sale/static/src/css/chrome50.css');
                }
            }

            if (this.env.pos.config.iface_big_scrollbars) {
                this.state.uiState.hasBigScrollBars = true;
            }

            this._disableRubberbanding();
            this._disableBackspaceBack();
            this._replaceCrashmanager();
        }
        // replaces the error handling of the existing crashmanager which
        // uses jquery dialog to display the error, to use the pos popup
        // instead
        _replaceCrashmanager() {
            var self = this;
            CrashManager.include({
                show_error: function(error) {
                    if (self.env.pos) {
                        // self == this component
                        self.showPopup('ErrorTracebackPopup', {
                            title: error.type,
                            body: error.message + '\n' + error.data.debug + '\n',
                        });
                    } else {
                        // this == CrashManager instance
                        this._super(error);
                    }
                },
            });
        }
        _disableRubberbanding() {
            var self = this;

            document.body.addEventListener('touchstart', function(event) {
                self.previous_touch_y_coordinate = event.touches[0].clientY;
            });

            // prevent the pos body from being scrollable.
            document.body.addEventListener('touchmove', function(event) {
                var node = event.target;
                var current_touch_y_coordinate = event.touches[0].clientY;
                var scrolling_down;

                if (current_touch_y_coordinate < self.previous_touch_y_coordinate) {
                    scrolling_down = true;
                } else {
                    scrolling_down = false;
                }

                while (node) {
                    if (
                        node.classList &&
                        node.classList.contains('touch-scrollable') &&
                        self._scrollable(node, scrolling_down)
                    ) {
                        return;
                    }
                    node = node.parentNode;
                }
                event.preventDefault();
            });
        }
        // prevent backspace from performing a 'back' navigation
        _disableBackspaceBack() {
            $(document).on('keydown', function(e) {
                if (e.which === 8 && !$(e.target).is('input, textarea')) {
                    e.preventDefault();
                }
            });
        }
        _scrollable(element, scrolling_down) {
            var $element = $(element);
            var scrollable = true;

            if (!scrolling_down && $element.scrollTop() <= 0) {
                scrollable = false;
            } else if (
                scrolling_down &&
                $element.scrollTop() + $element.height() >= element.scrollHeight
            ) {
                scrollable = false;
            }

            return scrollable;
        }
    }

    Registry.add(Chrome.name, Chrome);

    return { Chrome };
});
