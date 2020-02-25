odoo.define('point_of_sale.SaleDetailsButton', function(require) {
    'use strict';

    const { Chrome } = require('point_of_sale.chrome');
    const { PosComponent } = require('point_of_sale.PosComponent');

    class SaleDetailsButton extends PosComponent {
        async onClick() {
            const result = await this.rpc({
                model: 'report.point_of_sale.report_saledetails',
                method: 'get_sale_details',
                args: [false, false, false, [this.env.pos.pos_session.id]],
            });
            const report = this.env.qweb.renderToString('SaleDetailsReport', {
                ...result,
                date: new Date().toLocaleString(),
                pos: this.env.pos,
            });
            this.env.pos.proxy.printer.print_receipt(report);
        }
    }

    Chrome.addComponents([SaleDetailsButton]);

    return { SaleDetailsButton };
});
