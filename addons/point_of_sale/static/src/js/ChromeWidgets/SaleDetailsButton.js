odoo.define('point_of_sale.SaleDetailsButton', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');
    const { renderToString } = require('@web/core/utils/render');

    class SaleDetailsButton extends PosComponent {
        async onClick() {
            // IMPROVEMENT: Perhaps put this logic in a parent component
            // so that for unit testing, we can check if this simple
            // component correctly triggers an event.
            const saleDetails = await this.rpc({
                model: 'report.point_of_sale.report_saledetails',
                method: 'get_sale_details',
                args: [false, false, false, [this.env.pos.pos_session.id]],
            });
            const report = renderToString(
                'SaleDetailsReport',
                Object.assign({}, saleDetails, {
                    date: new Date().toLocaleString(),
                    pos: this.env.pos,
                })
            );
            const printResult = await this.env.proxy.printer.print_receipt(report);
            if (!printResult.successful) {
                await this.showPopup('ErrorPopup', {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
            }
        }
    }
    SaleDetailsButton.template = 'SaleDetailsButton';

    Registries.Component.add(SaleDetailsButton);

    return SaleDetailsButton;
});
