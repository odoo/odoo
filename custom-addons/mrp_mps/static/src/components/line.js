/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { useService, useBus } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { Component, useRef, onPatched } from "@odoo/owl";

export default class MpsLineComponent extends Component {

    setup() {
        this.actionService = useService("action");
        this.dialogService = useService("dialog");
        this.orm = useService("orm");
        this.model = this.env.model;
        this.forecastRow = useRef("forecastRow");
        this.replenishRow = useRef("replenishRow");

        onPatched(() => {
            // after a replenishment, switch to next column if possible
            const previousEl = this.replenishRow.el.getElementsByClassName('o_mrp_mps_hover')[0];
            if (previousEl) {
                previousEl.classList.remove('o_mrp_mps_hover');
                const el = this.replenishRow.el.getElementsByClassName('o_mrp_mps_forced_replenish')[0];
                if (el) {
                    el.classList.add('o_mrp_mps_hover');
                }
            }
        });

        useBus(this.model, 'mouse-over', () => this._onMouseOverReplenish());
        useBus(this.model, 'mouse-out', () => this._onMouseOutReplenish());
    }

    get productionSchedule() {
        return this.props.data;
    }

    get groups() {
        return this.props.groups;
    }

    get isSelected() {
        return this.model.selectedRecords.has(this.productionSchedule.id);
    }

    formatFloat(value) {
        return formatFloat(value, { digits: [false, this.productionSchedule.precision_digits] });
    }

    /**
     * Handles the click on replenish button. It will call action_replenish with
     * all the Ids present in the view.
     * @private
     * @param {Integer} id mrp.production.schedule Id.
     */
    _onClickReplenish(id) {
        this.model._actionReplenish([id]);
    }

    /**
     * Handles the click on product name. It will open the product form view
     * @private
     * @param {MouseEvent} ev
     */
    _onClickRecordLink(ev) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: ev.currentTarget.dataset.model,
            res_id: Number(ev.currentTarget.dataset.resId),
            views: [[false, 'form']],
            target: 'current',
        });
    }

    /**
     * Handles the click on `min..max` or 'targeted stock' Event. It will open
     * a form view in order to edit a production schedule and update the
     * template on save.
     *
     * @private
     * @param {MouseEvent} ev
     * @param {Integer} id mrp.production.schedule Id.
     */
    _onClickEdit(ev, id) {
        this.model._editProduct(id);
    }

    /**
     * Handles the click on unlink button. A dialog ask for a confirmation and
     * it will unlink the product.
     * @private
     * @param {Object} id mrp.production.schedule Id.
     */
    _onClickUnlink(id) {
        this.model._unlinkProduct([id]);
    }

    _onClickOpenDetails(ev) {
        const dateStart = ev.target.dataset.date_start;
        const dateStop = ev.target.dataset.date_stop;
        const dateStr = this.model.data.dates[ev.target.dataset.date_index];
        const action = ev.target.dataset.action;
        const productionScheduleId = Number(ev.target.closest('.o_mps_content').dataset.id);
        this.model._actionOpenDetails(productionScheduleId, action, dateStr, dateStart, dateStop);
    }

    /**
     * Handles the change on a forecast cell.
     * @private
     * @param {Event} ev
     * @param {Object} productionScheduleId mrp.production.schedule Id.
     */
    _onChangeForecast(ev, productionScheduleId) {
        const dateIndex = parseInt(ev.target.dataset.date_index);
        const forecastQty = ev.target.value;
        if (forecastQty === "" || isNaN(forecastQty)) {
            ev.target.value = this.model._getOriginValue(productionScheduleId, dateIndex, 'forecast_qty');
        } else {
            this.model._saveForecast(productionScheduleId, dateIndex, forecastQty).then(() => {
                const inputSelector = 'input[data-date_index="' + (dateIndex + 1) + '"]';
                const nextInput = this.forecastRow.el.querySelector(inputSelector);
                if (nextInput) {
                    nextInput.select();
                }
            }, () => {
                ev.target.value = this.model._getOriginValue(productionScheduleId, dateIndex, 'forecast_qty');
            });
        }
    }

    /**
     * Handles the quantity To Replenish change on a forecast cell.
     * @private
     * @param {Event} ev
     * @param {Object} productionScheduleId mrp.production.schedule Id.
     */
    _onChangeToReplenish(ev, productionScheduleId) {
        const dateIndex = parseInt(ev.target.dataset.date_index);
        const replenishQty = ev.target.value;
        if (replenishQty === "" || isNaN(replenishQty)) {
            ev.target.value = this.model._getOriginValue(productionScheduleId, dateIndex, 'replenish_qty');
        } else {
            this.model._saveToReplenish(productionScheduleId, dateIndex, replenishQty).then(() => {
                const inputSelector = 'input[data-date_index="' + (dateIndex + 1) + '"]';
                const nextInput = this.replenishRow.el.querySelector(inputSelector);
                if (nextInput) {
                    nextInput.select();
                }
            }, () => {
                ev.target.value = this.model._getOriginValue(productionScheduleId, dateIndex, 'replenish_qty');
            });
        }
    }

    async _onClickForecastReport() {
        const action = await this.orm.call(
            "product.product",
            "action_product_forecast_report",
            [[this.productionSchedule.id]],
        );
        action.context = {
            active_model: "product.product",
            active_id: this.productionSchedule.product_id[0],
            warehouse_id: this.productionSchedule.warehouse_id && this.productionSchedule.warehouse_id[0],
        };
        return this.actionService.doAction(action);
    }

    _onClickAutomaticMode(ev, productionScheduleId) {
        const dateIndex = parseInt(ev.target.dataset.date_index);
        this.model._removeQtyToReplenish(productionScheduleId, dateIndex);
    }

    _onFocusInput(ev) {
        ev.target.select();
    }

    _onMouseOverReplenish(ev) {
        const el = this.replenishRow.el.getElementsByClassName('o_mrp_mps_forced_replenish');
        if (el && el[0]) {
            el[0].classList.add('o_mrp_mps_hover');
        }
    }

    _onMouseOutReplenish(ev) {
        const el = this.replenishRow.el.getElementsByClassName('o_mrp_mps_hover');
        if (el && el[0]) {
            el[0].classList.remove('o_mrp_mps_hover');
        }
    }

    toggleSelection(ev, productionScheduleId) {
        this.model.toggleRecordSelection(productionScheduleId);
    }

}

MpsLineComponent.template = 'mrp_mps.MpsLineComponent';
MpsLineComponent.components = {
    CheckBox,
};
