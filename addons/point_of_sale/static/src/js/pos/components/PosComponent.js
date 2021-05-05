/** @odoo-module alias=point_of_sale.PosComponent **/

const { Component } = owl;

class PosComponent extends Component {
    showTempScreen(name, props) {
        return new Promise((resolve) => {
            this.trigger('show-temp-screen', { name, props, resolve });
        });
    }
    /**
     * @see PointOfSaleModel.uirpc
     */
    uirpc() {
        return this.env.model.uirpc(...arguments);
    }
}

export default PosComponent;
