odoo.define('pos_restaurant.TableWidget', function(require) {
    'use strict';

    const { PosComponent } = require('point_of_sale.PosComponent');
    const Registry = require('point_of_sale.ComponentsRegistry');

    class TableWidget extends PosComponent {
        static template = 'TableWidget';
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
            Object.assign(tableCover.style, { height: `${Math.ceil(this.fill * 100)}%` })
        }
        get fill() {
            const customerCount = this.env.pos.get_customer_count(this.props.table);
            return Math.min(1, Math.max(0, customerCount / this.props.table.seats));
        }
    }

    Registry.add('TableWidget', TableWidget);

    return { TableWidget };
});
