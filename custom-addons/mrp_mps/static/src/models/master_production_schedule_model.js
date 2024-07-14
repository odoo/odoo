/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Mutex } from "@web/core/utils/concurrency";
import { EventBus } from "@odoo/owl";

export class MasterProductionScheduleModel extends EventBus {
    constructor(params, services) {
        super();
        this.domain = [];
        this.offset = 0;
        this.limit = false;
        this.params = params;
        this.orm = services.orm;
        this.action = services.action;
        this.dialog = services.dialog;
        this.selectedRecords = new Set();
        this.mutex = new Mutex();
    }

    async load(domain, offset, limit) {
        if (domain !== undefined) {
            this.domain = domain;
        }
        if (offset !== undefined) {
            this.offset = offset;
        }
        if (limit !== undefined) {
            this.limit = limit;
        }
        this.data = await this.orm.call('mrp.production.schedule', 'get_mps_view_state', [this.domain, this.offset, this.limit]);
        this.notify();
    }

    async reload(productionScheduleId) {
        return await this.orm.call(
            'mrp.production.schedule',
            'get_impacted_schedule',
            [productionScheduleId, this.domain],
        ).then((productionScheduleIds) => {
            productionScheduleIds.push(productionScheduleId);
            return this.orm.call(
                'mrp.production.schedule',
                'get_production_schedule_view_state',
                [productionScheduleIds],
            );
        }).then((production_schedule_ids) => {
            for (var i = 0; i < production_schedule_ids.length; i++) {
                const index = this.data.production_schedule_ids.findIndex(ps => ps.id === production_schedule_ids[i].id);
                if (index >= 0) {
                    this.data.production_schedule_ids.splice(index, 1, production_schedule_ids[i]);
                } else {
                    this.data.production_schedule_ids.push(production_schedule_ids[i]);
                }
            }
            this.notify();
        });
    }

    notify() {
        this.unselectAll();
        this.trigger('update');
    }

    /**
     * Make an rpc to replenish the different schedules passed as arguments.
     * If the procurementIds list is empty, it replenish all the schedules under
     * the current domain. Reload the content after the replenish in order to
     * display the new forecast cells to run.
     * @private
     * @param {Integer[]} productionScheduleIds mrp.production.schedule ids to
     * replenish.
     * @return {Promise}
     */
    _actionReplenish(productionScheduleIds, basedOnLeadTime = false) {
        this.mutex.exec(() => {
            return this.orm.call(
                'mrp.production.schedule',
                'action_replenish',
                [productionScheduleIds, basedOnLeadTime],
            ).then(() => {
                if (productionScheduleIds.length === 1) {
                    this.reload(productionScheduleIds[0]);
                } else {
                    this.load();
                }
            });
        });
    }

    replenishAll() {
        this.orm.search("mrp.production.schedule", this.domain).then((ids) => {
            this._actionReplenish(ids, true);
        });
    }

    replenishSelectedRecords() {
        this._actionReplenish(Array.from(this.selectedRecords), false);
    }

    /**
     * Save the forecasted quantity and reload the current schedule in order
     * to update its To Replenish quantity and its safety stock (current and
     * future period). Also update the other schedules linked by BoM in order
     * to update them depending the indirect demand.
     * @private
     * @param {Integer} productionScheduleId mrp.production.schedule Id.
     * @param {Integer} dateIndex period to save (column number)
     * @param {Float} forecastQty The new forecasted quantity
     * @return {Promise}
     */
    _saveForecast(productionScheduleId, dateIndex, forecastQty) {
        return this.mutex.exec(() => {
            this.orm.call(
                'mrp.production.schedule',
                'set_forecast_qty',
                [productionScheduleId, dateIndex, forecastQty],
            ).then(() => {
                return this.reload(productionScheduleId);
            });
        });
    }

    /**
     * Open the mrp.production.schedule form view in order to create the record.
     * Once the record is created get its state and render it.
     * @private
     * @return {Promise}
     */
    _createProduct() {
        this.mutex.exec(() => {
            this.action.doAction('mrp_mps.action_mrp_mps_form_view', {
                onClose: () => this.load(),
            });
        });
    }

    /**
     * Open the mrp.production.schedule form view in order to edit the record.
     * Once the record is edited get its state and render it.
     * @private
     * @param {Integer} productionScheduleId mrp.production.schedule Id.
     */
    _editProduct(productionScheduleId) {
        this.mutex.exec(() => {
            this.action.doAction({
                name: 'Edit Production Schedule',
                type: 'ir.actions.act_window',
                res_model: 'mrp.production.schedule',
                views: [[false, 'form']],
                target: 'new',
                res_id: productionScheduleId,
            }, {
                onClose: () => this.reload(productionScheduleId),
            });
        });
    }

    /**
     * Unlink the production schedule and remove it from the DOM. Use a
     * confirmation dialog in order to avoid a mistake from the user.
     * @private
     * @param {Integer[]} productionScheduleIds mrp.production.schedule Ids.
     * @return {Promise}
     */
    _unlinkProduct(productionScheduleIds) {
        function doIt() {
            this.mutex.exec(async () => {
                return Promise.all(productionScheduleIds.map((id) => this.orm.unlink(
                    'mrp.production.schedule',
                    [id]
                ))).then(() => {
                    for (const productionScheduleId of productionScheduleIds) {
                        const index = this.data.production_schedule_ids.findIndex(ps => ps.id === productionScheduleId);
                        this.data.production_schedule_ids.splice(index, 1);
                    }
                    this.notify();
                });
            });
        }
        const body = productionScheduleIds.length > 1
            ? _t("Are you sure you want to delete these records?")
            : _t("Are you sure you want to delete this record?");
        this.dialog.add(ConfirmationDialog, {
            body: body,
            title: _t("Confirmation"),
            confirm: doIt.bind(this),
        });
    }

    unlinkSelectedRecord() {
        return this._unlinkProduct(Array.from(this.selectedRecords));
    }

    /**
     *
     * @param {Integer} productionScheduleId mrp.production.schedule Id
     * @param {String} action name of the action to be undertaken
     * @param {String} dateStr name of the period
     * @param {String} dateStart start date of the period
     * @param {String} dateStop end date of the period
     * @return {Promise}
     */
    _actionOpenDetails(productionScheduleId, action, dateStr, dateStart, dateStop) {
        this.mutex.exec(() => {
            return this.orm.call(
                'mrp.production.schedule',
                action,
                [productionScheduleId, dateStr, dateStart, dateStop]
            ).then((action) => {
                return this.action.doAction(action);
            });
        });
    }

    /**
     * Save the quantity To Replenish and reload the current schedule in order
     * to update it's safety stock and quantity in future period. Also mark
     * the cell with a blue background in order to show that it was manually
     * updated.
     * @private
     * @param {Integer} productionScheduleId mrp.production.schedule Id.
     * @param {Integer} dateIndex period to save (column number)
     * @param {Float} replenishQty The new quantity To Replenish
     * @return {Promise}
     */
    _saveToReplenish(productionScheduleId, dateIndex, replenishQty) {
        return this.mutex.exec(() => {
            this.orm.call(
                'mrp.production.schedule',
                'set_replenish_qty',
                [productionScheduleId, dateIndex, replenishQty],
            ).then(() => {
                return this.reload(productionScheduleId);
            });
        });
    }

    /**
     * Remove the manual change of replenishQty and load the suggested value.
     * @private
     * @param {Integer} productionScheduleId mrp.production.schedule Id.
     * @param {Integer} dateIndex period to save (column number)
     * @return {Promise}
     */
    _removeQtyToReplenish(productionScheduleId, dateIndex) {
        return this.mutex.exec(() => {
            this.orm.call(
                'mrp.production.schedule',
                'remove_replenish_qty',
                [productionScheduleId, dateIndex]
            ).then(() => {
                return this.reload(productionScheduleId);
            });
        });
    }

    _getOriginValue(productionScheduleId, dateIndex, inputName) {
        return this.data.production_schedule_ids.find(ps => ps.id === productionScheduleId).forecast_ids[dateIndex][inputName];
    }

    /**
     * Save the company settings and hide or display the rows.
     * @private
     * @param {Object} values {field_name: field_value}
     */
    _saveCompanySettings(values) {
        this.mutex.exec(() => {
            this.orm.write(
                'res.company',
                [this.data.company_id],
                values,
            ).then(() => {
                this.load();
            });
        });
    }

    mouseOverReplenish() {
        this.trigger('mouse-over');
    }

    mouseOutReplenish() {
        this.trigger('mouse-out');
    }

    selectAll() {
        this.data.production_schedule_ids.map(
            ({ id }) => this.selectedRecords.add(id)
        );
    }

    unselectAll() {
        this.selectedRecords.clear();
    }

    toggleRecordSelection(productionScheduleId) {
        if (this.selectedRecords.has(productionScheduleId)) {
            this.selectedRecords.delete(productionScheduleId);
        } else {
            this.selectedRecords.add(productionScheduleId);
        }
        this.trigger('update');
    }

    toggleSelection() {
        if (this.selectedRecords.size === this.data.production_schedule_ids.length) {
            this.unselectAll();
        } else {
            this.selectAll();
        }
        this.trigger('update');
    }

}
