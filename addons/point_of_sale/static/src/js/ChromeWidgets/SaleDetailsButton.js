odoo.define('point_of_sale.SaleDetailsButton', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent, addComponents } = require('point_of_sale.PosComponent');

    class SaleDetailsButton extends PosComponent {
        static template = 'SaleDetailsButton';
        async onClick() {
            const saleDetails = await this.rpc({
                model: 'report.point_of_sale.report_saledetails',
                method: 'get_sale_details',
                args: [false, false, false, [this.env.pos.pos_session.id]],
            });
            const report = this.env.qweb.renderToString('SaleDetailsReport', {
                ...saleDetails,
                date: new Date().toLocaleString(),
                pos: this.env.pos,
            });
            const printResult = await this.env.pos.proxy.printer.print_receipt(report);
            if (!printResult.successful) {
                await this.showPopup('ErrorPopup', {
                    title: printResult.message.title,
                    body: printResult.message.body,
                });
            }
        }
    }

    addComponents(Chrome, [SaleDetailsButton]);

    return { SaleDetailsButton };
});
