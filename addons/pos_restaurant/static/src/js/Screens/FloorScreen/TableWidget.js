odoo.define('pos_restaurant.TableWidget', function (require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');

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
            const nCustomers = this.env.model.getTotalNumberCustomers(this.props.table);
            return Math.min(1, Math.max(0, nCustomers / this.props.table.seats));
        }
        get orderCountClass() {
            const notifications = this._getNotifications();
            return {
                'order-count': true,
                'notify-printing': notifications.printing,
                'notify-skipped': notifications.skipped,
            };
        }
        get customerCountDisplay() {
            const nCustomers = this.env.model.getTotalNumberCustomers(this.props.table);
            return `${nCustomers}/${this.props.table.seats}`;
        }
        getTableOrderCount(table) {
            if (table.id in this.env.model.data.uiState.FloorScreen.tableBackendOrdersCount) {
                return this.env.model.data.uiState.FloorScreen.tableBackendOrdersCount[table.id];
            } else {
                return this.env.model.getOrderCount(table);
            }
        }
        _getNotifications() {
            let hasChangesCount = 0;
            let hasSkippedCount = 0;
            for (const order of this.env.model.getTableOrders(this.props.table)) {
                if (this.env.model.hasResumeChangesToPrint(order)) {
                    hasChangesCount++;
                } else if (this.env.model.hasSkippedResumeChanges(order)) {
                    hasSkippedCount++;
                }
            }
            return hasChangesCount ? { printing: true } : hasSkippedCount ? { skipped: true } : {};
        }
    }
    TableWidget.template = 'pos_restaurant.TableWidget';

    return TableWidget;
});
