odoo.define('point_of_sale.ClientScreenButton', function(require) {
    'use strict';

    const { useState } = owl;
    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    // Formerly ClientScreenWidget
    class ClientScreenButton extends PosComponent {
        constructor() {
            super(...arguments);
            this.local = this.env.pos.config.iface_customer_facing_display_local && !this.env.pos.config.iface_customer_facing_display_proxy;
            this.state = useState({ status: this.local ? 'success' : 'failure' });
            this._start();
        }
        get message() {
            return {
                success: '',
                warning: this.env._t('Connected, Not Owned'),
                failure: this.env._t('Disconnected'),
                not_found: this.env._t('Client Screen Unsupported. Please upgrade the IoT Box'),
            }[this.state.status];
        }
        onClick() {
            if (this.local) {
                return this.onClickLocal();
            } else {
                return this.onClickProxy();
            }
        }
        async onClickLocal() {
            this.env.pos.customer_display = window.open('', 'Customer Display', 'height=600,width=900');
            const renderedHtml = await this.env.pos.render_html_for_customer_facing_display();
            var $renderedHtml = $('<div>').html(renderedHtml);
            $(this.env.pos.customer_display.document.body).html($renderedHtml.find('.pos-customer_facing_display'));
            $(this.env.pos.customer_display.document.head).html($renderedHtml.find('.resources').html());
        }
        async onClickProxy() {
            try {
                const renderedHtml = await this.env.pos.render_html_for_customer_facing_display();
                let ownership = await this.env.pos.proxy.take_ownership_over_client_screen(
                    renderedHtml
                );
                if (typeof ownership === 'string') {
                    ownership = JSON.parse(ownership);
                }
                if (ownership.status === 'success') {
                    this.state.status = 'success';
                } else {
                    this.state.status = 'warning';
                }
                if (!this.env.pos.proxy.posbox_supports_display) {
                    this.env.pos.proxy.posbox_supports_display = true;
                    this._start();
                }
            } catch (error) {
                if (typeof error == 'undefined') {
                    this.state.status = 'failure';
                } else {
                    this.state.status = 'not_found';
                }
            }
        }
        _start() {
            if (this.local) {
                return;
            }

            const self = this;
            async function loop() {
                if (self.env.pos.proxy.posbox_supports_display) {
                    try {
                        let ownership = await self.env.pos.proxy.test_ownership_of_client_screen();
                        if (typeof ownership === 'string') {
                            ownership = JSON.parse(ownership);
                        }
                        if (ownership.status === 'OWNER') {
                            self.state.status = 'success';
                        } else {
                            self.state.status = 'warning';
                        }
                        setTimeout(loop, 3000);
                    } catch (error) {
                        if (error.abort) {
                            // Stop the loop
                            return;
                        }
                        if (typeof error == 'undefined') {
                            self.state.status = 'failure';
                        } else {
                            self.state.status = 'not_found';
                            self.env.pos.proxy.posbox_supports_display = false;
                        }
                        setTimeout(loop, 3000);
                    }
                }
            }
            loop();
        }
    }
    ClientScreenButton.template = 'ClientScreenButton';

    Registries.Component.add(ClientScreenButton);

    return ClientScreenButton;
});
