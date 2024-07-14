/** @odoo-module **/

import MainComponent from "@stock_barcode/components/main";
import BarcodeMRPModel from "../models/barcode_mrp_model";
import HeaderComponent from "./header";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(MainComponent.prototype, {
    setup() {
        super.setup();
        this.state = useState({ ...this.state, displayByProduct: false });
    },

    get displayActionButtons() {
        return super.displayActionButtons && !this.state.displayByProduct;
    },

    get produceBtnLabel() {
        if (this.env.model.record.qty_producing < this.env.model.record.product_qty){
            return _t('Produce');
        }
        return _t('Produce All');
    },

    get headerFormViewProps() {
        return {
            resId: this.resId || this.env.model.record.id,
            resModel: this.resModel,
            context: { set_qty_producing: true },
            viewId: this.env.model.headerViewId,
            display: { controlPanel: false },
            type: "form",
            onSave: (record) => this.saveFormView(record),
            onDiscard: () => this.toggleBarcodeLines(),
        };
    },

    get lineFormViewProps() {
        const res = super.lineFormViewProps;
        const params = { newByProduct: this.state.displayByProduct };
        res.context = this.env.model._getNewLineDefaultContext(params);
        return res;
    },

    get lines() {
        return this.env.model.groupedLines;
    },

    get addLineBtnName() {
        if (this.env.model.resModel == 'mrp.production' && this.env.model.record.product_id) {
            return _t('Add Component');
        }
        return super.addLineBtnName;
    },

    exit(ev) {
        if (this.state.view === "barcodeLines" && this.state.displayByProduct) {
            this.state.displayByProduct = false;
            this.env.model.displayByProduct = false;
        } else {
            super.exit(...arguments);
        }
    },

    async cancel() {
        if (this.resModel == 'mrp.production') {
            await new Promise((resolve) => {
                this.dialog.add(ConfirmationDialog, {
                    body: _t("Are you sure you want to cancel this manufacturing order?"),
                    title: _t("Cancel manufacturing order?"),
                    cancel: () => {},
                    confirm: async () => {
                        await this.orm.call(
                            this.resModel,
                            'action_cancel',
                            [[this.env.model.resId]]
                        );
                        resolve();
                    },
                });
            });
            this.env.model._cancelNotification();
            this.env.config.historyBack();
            return;
        }
        await super.cancel(...arguments);
    },

    async toggleHeaderView() {
        await this.env.model.save();
        this.state.view = 'headerProductPage';
    },

    openByProductLines() {
        this._editedLineParams = undefined;
        this.state.displayByProduct = true;
        this.env.model.displayByProduct = true;
    },

    async newScrapProduct() {
        await this.env.model.save();
        await this.env.model._scrap();
    },

    onOpenProductPage(line) {
        if (this.resModel == 'mrp.production' && !this.env.model.record.product_id) {
            this.toggleHeaderView();
            return;
        }
        return super.onOpenProductPage(...arguments);
    },

    async saveFormView(lineRecord) {
        if (lineRecord.resModel === 'mrp.production') {
            const recordId = lineRecord.resId;
            let update = Boolean(this.resId);
            if (!this.resId) {
                this.resId = recordId;
                await this.env.model.confirmAndSetData(recordId);
                this.toggleBarcodeLines();
            }
            if (lineRecord.context.set_qty_producing === true && lineRecord.data.lot_producing_id != this.env.model.record.lot_producing_id){
                await this.orm.call('mrp.production', 'set_qty_producing', [[recordId]]);
                update = true;
            }
            if (update) {
                if (lineRecord.data.product_qty != this.env.model.record.product_qty) {
                    // need to reassign moves to update the quants on screen
                    await this.orm.call(
                        this.resModel,
                        'action_assign',
                        [[this.resId]]
                    );
                }
                this._onRefreshState({ recordId });
            }
            return;
        }
        return super.saveFormView(...arguments);
    },

    async _onRefreshByProducts() {
        const { route, params } = this.env.model.getActionRefresh(this.resId);
        const result = await this.rpc(route, params);
        await this.env.model.refreshCache(result.data.records);
        this.openByProductLines();
    },

    onValidateByProduct() {
        this.state.displayByProduct = false;
        this.env.model.displayByProduct = false;
        this.toggleBarcodeLines();
    },

    _getModel() {
        const { resId, resModel, rpc, notification, orm, action } = this;
        if (this.resModel === 'mrp.production') {
            return new BarcodeMRPModel(resModel, resId, { rpc, notification, orm, action });
        }
        return super._getModel(...arguments);
    },

    _getHeaderHeight() {
        const headerHeight = super._getHeaderHeight();
        const mo_header = document.querySelector('.o_header');
        return mo_header ? headerHeight + mo_header.offsetHeight: headerHeight;
    },
});

MainComponent.components.Header = HeaderComponent;
