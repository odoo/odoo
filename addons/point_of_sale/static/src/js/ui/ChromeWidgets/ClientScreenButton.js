/** @odoo-module alias=point_of_sale.ClientScreenButton **/

const { useState } = owl;
import PosComponent from 'point_of_sale.PosComponent';

class ClientScreenButton extends PosComponent {
    constructor() {
        super(...arguments);
        this.state = useState({ status: 'success' });
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
    get local() {
        return (
            this.env.model.config.iface_customer_facing_display_local &&
            !this.env.model.config.iface_customer_facing_display_via_proxy
        );
    }
    async onClick() {
        if (this.local) {
            return this._onClickLocal();
        } else {
            return this._onClickProxy();
        }
    }
    async _onClickLocal() {
        this.env.model.customerDisplayWindow = window.open('', 'Customer Display', 'height=600,width=900');
        const renderedHtml = await this.env.model.renderCustomerDisplay();
        var $renderedHtml = $('<div>').html(renderedHtml);
        $(this.env.model.customerDisplayWindow.document.body).html($renderedHtml.find('.pos-customer_facing_display'));
        $(this.env.model.customerDisplayWindow.document.head).html($renderedHtml.find('.resources').html());
    }
    async _onClickProxy() {
        try {
            const renderedHtml = await this.env.model.renderCustomerDisplay();
            const ownership = await this.env.model.proxy.take_ownership_over_client_screen(renderedHtml);
            if (typeof ownership === 'string') {
                ownership = JSON.parse(ownership);
            }
            if (ownership.status === 'success') {
                this.state.status = 'success';
            } else {
                this.state.status = 'warning';
            }
            if (!this.env.model.proxy.posbox_supports_display) {
                this.env.model.proxy.posbox_supports_display = true;
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
        // QUESTION: Why is there a need to loop when it already has the ownership?
        const loop = async () => {
            if (this.env.model.proxy.posbox_supports_display) {
                try {
                    const ownership = await this.env.model.proxy.test_ownership_of_client_screen();
                    if (typeof ownership === 'string') {
                        ownership = JSON.parse(ownership);
                    }
                    if (ownership.status === 'OWNER') {
                        this.state.status = 'success';
                    } else {
                        this.state.status = 'warning';
                    }
                    setTimeout(loop, 3000);
                } catch (error) {
                    if (error.abort) {
                        // Stop the loop
                        return;
                    }
                    if (typeof error == 'undefined') {
                        this.state.status = 'failure';
                    } else {
                        this.state.status = 'not_found';
                        this.env.model.proxy.posbox_supports_display = false;
                    }
                    setTimeout(loop, 3000);
                }
            }
        };
        loop();
    }
}
ClientScreenButton.template = 'point_of_sale.ClientScreenButton';

export default ClientScreenButton;
