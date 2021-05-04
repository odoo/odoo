/** @odoo-module alias=point_of_sale.PosComponent **/

const { Component } = owl;

class PosComponent extends Component {
    showTempScreen(name, props) {
        return new Promise((resolve) => {
            this.trigger('show-temp-screen', { name, props, resolve });
        });
    }
    async rpc() {
        return await this.env.model._rpc(...arguments);
    }
}

export default PosComponent;
