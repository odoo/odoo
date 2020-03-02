odoo.define('point_of_sale.chrome', function(require) {
    'use strict';

    const { useState, useRef } = owl.hooks;
    const { debounce } = owl.utils;
    const { PosComponent } = require('point_of_sale.PosComponent');
    const { PosModel } = require('point_of_sale.models');
    const { useListener } = require('web.custom_hooks');
    const { CrashManager } = require('web.CrashManager');
    const { BarcodeEvents } = require('barcodes.BarcodeEvents');
    const { loadCSS } = require('web.ajax');

    /**
     * Chrome is the root component of the PoS App.
     */
    class Chrome extends PosComponent {
        constructor() {
            super(...arguments);
            useListener('show-screen', this.showScreen);
            useListener('pos-error', this.onPosError);
            useListener('toggle-debug-widget', debounce(this._toggleDebugWidget, 100));
            useListener('show-popup', this.__showPopup);
            useListener('close-popup', this.__closePopup);
            useListener('show-temp-screen', this.__showTempScreen);
            useListener('close-temp-screen', this.__closeTempScreen);
            useListener('close-pos', this._closePos);
            useListener('loading-skip-callback', () => this._loadingSkipCallback());

            this.state = useState({
                uiState: 'LOADING', // 'LOADING' | 'READY' | 'CLOSING'
                debugWidgetIsShown: true,
                hasBigScrollBars: false,
            });

            this.loading = useState({
                message: 'Loading',
                skipButtonIsShown: false,
            });

            this.mainScreen = useState({
                name: 'ProductScreen',
                component: this.constructor.components.ProductScreen,
            });
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
                this.env.pos = new PosModel(posModelDefaultAttributes);
                await this.env.pos.ready;
                this._buildChrome();
                this.state.uiState = 'READY';
                this.trigger('show-screen', { name: 'ProductScreen' });
                this.env.pos.push_order(); // push order in the background, no need to await
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

        __showPopup(event) {
            const { name, props, resolve, numberBuffer } = event.detail;
            this.popup.isShown = true;
            this.popup.name = name;
            this.popup.component = this.constructor.components[name];
            this.popupProps = { ...props, resolve, numberBuffer };
            if (numberBuffer) {
                numberBuffer.pause();
            }
        }
        __closePopup() {
            this.popup.isShown = false;
            if (this.popupProps.numberBuffer) {
                this.popupProps.numberBuffer.resume();
            }
        }
        __showTempScreen(event) {
            const { name, props, resolve, numberBuffer } = event.detail;
            this.tempScreen.isShown = true;
            this.tempScreen.name = name;
            this.tempScreen.component = this.constructor.components[name];
            this.tempScreenProps = { ...props, resolve, numberBuffer };
            // hide main screen
            this.mainScreen.isShown = false;
            // pause numberBuffer
            if (numberBuffer) {
                numberBuffer.pause();
            }
        }
        __closeTempScreen() {
            this.tempScreen.isShown = false;
            // show main screen
            this.mainScreen.isShown = true;
            // resume numberBuffer
            if (this.tempScreenProps.numberBuffer) {
                this.tempScreenProps.numberBuffer.resume();
            }
        }
        showScreen({ detail: { name, props } }) {
            this.mainScreen.isShown = true;
            this.mainScreen.name = name;
            this.mainScreen.component = this.constructor.components[name];
            this.mainScreenProps = props || {};
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
                    await this.env.pos.push_order();
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
            console.log(event.detail.error);
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

    return { Chrome };
});
