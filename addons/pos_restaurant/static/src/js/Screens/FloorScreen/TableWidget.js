/** @odoo-module */

import PosComponent from "@point_of_sale/js/PosComponent";
import Registries from "@point_of_sale/js/Registries";

/**
 * props: {
 *  onClick: callback,
 *  table: table object,
 * }
 */
class TableWidget extends PosComponent {
    setup() {
        owl.onMounted(this.onMounted);
    }
    onMounted() {
        const table = this.props.table;
        function unit(val) {
            return `${val}px`;
        }
        const style = {
            width: unit(table.width),
            height: unit(table.height),
            "line-height": unit(table.height),
            top: unit(table.position_v),
            left: unit(table.position_h),
            "border-radius": table.shape === "round" ? unit(1000) : "3px",
        };
        if (table.color) {
            style.background = table.color;
        }
        if (table.height >= 150 && table.width >= 150) {
            style["font-size"] = "32px";
        }
        Object.assign(this.el.style, style);

        const tableCover = this.el.querySelector(".table-cover");
        Object.assign(tableCover.style, { height: `${Math.ceil(this.fill * 100)}%` });
    }
    get fill() {
        const customerCount = this.env.pos.getCustomerCount(this.props.table.id);
        return Math.min(1, Math.max(0, customerCount / this.props.table.seats));
    }
    get orderCount() {
        const table = this.props.table;
        return table.order_count !== undefined
            ? table.order_count
            : this.env.pos
                  .getTableOrders(table.id)
                  .filter((o) => o.orderlines.length !== 0 || o.paymentlines.length !== 0).length;
    }
    get orderCountClass() {
        const countClass = { "order-count": true };
        if (this.env.pos.config.iface_printers) {
            const notifications = this._getNotifications();
            countClass["notify-printing"] = notifications.printing;
            countClass["notify-skipped"] = notifications.skipped;
        }
        return countClass;
    }
    get customerCountDisplay() {
        return `${this.env.pos.getCustomerCount(this.props.table.id)}/${this.props.table.seats}`;
    }
    _getNotifications() {
        const orders = this.env.pos.getTableOrders(this.props.table.id);

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
TableWidget.template = "TableWidget";

Registries.Component.add(TableWidget);

export default TableWidget;
