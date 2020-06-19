odoo.define('pos_restaurant.TableWidget', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class TableWidget extends PosComponent {
        mounted() {
            const table = this.props.table;
            function unit(val) {
                return `${val}px`;
            }
            const style = {
                width: unit(table.width),
                height: unit(table.height),
                'line-height': unit(table.height),
                top: unit(table.position_v),
                left: unit(table.position_h),
                'border-radius': table.shape === 'round' ? unit(1000) : '3px',
            };
            if (table.color) {
                style.background = table.color;
            }
            if (table.height >= 150 && table.width >= 150) {
                style['font-size'] = '32px';
            }
            Object.assign(this.el.style, style);

            const tableCover = this.el.querySelector('.table-cover');
            Object.assign(tableCover.style, { height: `${Math.ceil(this.fill * 100)}%` });
        }
        get fill() {
            const customerCount = this.env.pos.get_customer_count(this.props.table);
            return Math.min(1, Math.max(0, customerCount / this.props.table.seats));
        }
        get orderCount() {
            const table = this.props.table;
            return table.order_count !== undefined
                ? table.order_count
                : this.env.pos
                      .get_table_orders(table)
                      .filter(o => o.orderlines.length !== 0 || o.paymentlines.length !== 0).length;
        }
        get orderCountClass() {
            const notifications = this._getNotifications();
            return {
                'order-count': true,
                'notify-printing': notifications.printing,
                'notify-skipped': notifications.skipped,
            };
        }
        _getNotifications() {
            const orders = this.env.pos.get_table_orders(this.props.table);

            let hasChangesCount = 0;
            let hasSkippedCount = 0;
            for (let i = 0; i < orders.length; i++) {
                if (orders[i].hasChangesToPrint()) {
                    hasChangesCount++;
                } else if (orders[i].hasSkippedChanges()) {
                    hasSkippedCount++;
                }
            }

            return hasChangesCount ? { printing: true } : hasSkippedCount ? { skipped: true } : {};
        }
    }
    TableWidget.template = 'TableWidget';

    Registries.Component.add(TableWidget);

    return TableWidget;
});
