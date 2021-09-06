odoo.define('flexipharmacy.ProductScreen', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const ProductScreen = require('point_of_sale.ProductScreen');
    const NumberBuffer = require('point_of_sale.NumberBuffer');
    const {Gui} = require('point_of_sale.Gui');
    const {useListener} = require('web.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const {useRef, useState} = owl.hooks;
    const {isRpcError} = require('point_of_sale.utils');
    var rpc = require('web.rpc');

    const AsplRetProductScreenInh = (ProductScreen) =>
        class extends ProductScreen {
            constructor() {
                super(...arguments);
                useListener('button-click', this._onButtonClick);
                useListener('Click-Alternate-Product', this.ClickAlternateProduct);
                useListener('Cross-Selling-Product', this.CrossSellingProduct);
                useListener('close-warehouse-screen', this._closeWarehouse);
                useListener('show-warehouse-receipt', this._showWarehouseReceipt);
                useListener('click-doctor', this._onClickDoctor);
                useListener('select-line', this._changeWarehouseProduct);
                useListener('is_packaging', this.is_packaging_product);
                useListener('close-draft-screen', this.closeScreen);
                this.state.warehouse_mode = false;
                this.state.alternate_product = false;
                this.state.cross_selling_product = false;
                this.state.warehouseData = [];
                this.state.serials = [];
                this.state.isPackaging = false
                this.state.title = '';
            }
            async _onClickDoctor() {
                const currentClient = this.env.pos.get_order().get_client();
                const currentDoctor = this.env.pos.get_order().get_doctor();
                if (currentClient) {
                    const {confirmed, payload: newClient} = await this.showTempScreen(
                        'ReferenceClientListScreen', {doctor: currentDoctor, 'flag': 'show_doctor'});
                    if (confirmed) {
                        this.env.pos.get_order().set_doctor(newClient);
                    }
                } else {
                    alert('Please select customer !!');
                }
            }

            async product_lot_and_serial_number(product_id, isAllowOnlyOneLot) {
                var self = this
                var picking_type = this.env.pos.config.picking_type_id[0]
                var params = {
                    model: 'stock.production.lot',
                    method: 'product_lot_and_serial',
                    args: [product_id, product_id, picking_type]
                }
                await rpc.query(params).then(async function (serials) {
                    if (serials) {
                        for (var i = 0; i < serials.length; i++) {
                            if (serials[i].remaining_qty > 0) {
                                serials[i]['isSelected'] = false;
                                serials[i]['inputQty'] = 1;
                                if (serials[i].expiration_date) {
                                    let localTime = moment.utc(serials[i].expiration_date).toDate();
                                    serials[i]['expiration_date'] = moment(localTime).format('YYYY-MM-DD hh:mm A');
                                }
                                if (self.env.pos.config.product_exp_days) {
                                    let product_exp_date = moment().add(self.env.pos.config.product_exp_days, 'd')
                                        .format('YYYY-MM-DD');
                                    let serial_life = moment(serials[i]['expiration_date']).format('YYYY-MM-DD');
                                    if (product_exp_date >= serial_life) {
                                        serials[i]['NearToExpire'] = 'NearToExpire';
                                    }
                                }
                                self.state.serials.push(serials[i])
                            }
                        }
                        self.state.serials.sort(function (a, b) {
                            return (b.expiration_date) - (a.expiration_date);
                        });
                        self.showScreen('PackLotLineScreen', {
                            isSingleItem: isAllowOnlyOneLot,
                            serials: self.state.serials
                        });
                    }
                });
            }

            closeScreen() {
                this.trigger('show-orders-panel');
            }

            async _updateSelectedOrderline(event) {
                var selectedLine = this.currentOrder.get_selected_orderline();
                if (!this.currentOrder.is_empty() && this.currentOrder.get_order_total_discount_line() || (selectedLine && selectedLine.get_promotion())) {
                    let promotion = selectedLine.get_promotion();
                    if (promotion.promotion_type == 'discount_total') {
                        return false;
                    }
                }
                super._updateSelectedOrderline(event);
            }

            async _setValue(val) {
                if (this.env.pos.config.enable_pos_promotion && this.env.pos.user.access_pos_promotion) {
                    var selectedLine = this.currentOrder.get_selected_orderline();
                    var _lines = this.currentOrder.get_orderlines();

                    if (this.currentOrder.is_empty() || selectedLine.get_unique_child_id()) {
                        return;
                    }
                    if (val === 'remove' || !val) {
                        if (selectedLine && selectedLine.get_promotion()) {
                            var promotion = selectedLine.get_promotion();
                            const {confirmed} = await this.showPopup('ConfirmPopup', {
                                title: this.env._t('Contain' + promotion.promotion_code + 'Promotion'),
                                body: 'Are you sure you want to remove this line?',
                            });
                            if (!confirmed)
                                return;
                            if (_.contains(['quantity_discount', 'quantity_price', 'discount_on_multi_category'], promotion.promotion_type)) {
                                selectedLine.set_quantity(val);
                                selectedLine.set_unit_price(val);
                                selectedLine.set_discount(0);
                                selectedLine.set_promotion(false);
                            } else if (promotion.promotion_type == 'discount_on_multi_product') {
                                const combinationId = selectedLine.get_combination_id();
                                selectedLine.set_quantity(val);
                                selectedLine.set_unit_price(val);
                                _.each(_lines, function (line) {
                                    if (line.get_combination_id() === combinationId) {
                                        line.set_discount(0);
                                        line.set_combination_id();
                                        line.set_promotion(false);
                                    }
                                })
                                super._setValue(val);
                            } else if (promotion.promotion_type === 'buy_x_get_dis_y') {
                                selectedLine.set_promotion(null);
                                selectedLine.set_promotion_disc_child_id(null)
                                selectedLine.set_discount(0)
                                super._setValue(val);
                                this.currentOrder.apply_pos_order_discount_total();
                            }
                        } else if (selectedLine && selectedLine.get_unique_parent_id()) {
                            super._setValue(val);
                            var childLine = this.currentOrder.get_orderline_by_unique_id(selectedLine.get_unique_parent_id());
                            this.currentOrder.remove_orderline(childLine);
                            selectedLine.set_unique_parent_id(false)
                            this.currentOrder.apply_pos_order_discount_total();
                        } else if (selectedLine && selectedLine.get_promotion_disc_parent_id()) {
                            for (var _line of _lines) {
                                if (selectedLine.get_promotion_disc_parent_id() == _line.get_promotion_disc_child_id()) {
                                    _line.set_promotion(false);
                                    _line.set_promotion_disc_child_id(null);
                                    _line.set_discount(0)
                                }
                            }
                            selectedLine.set_promotion_disc_parent_id(null)
                            super._setValue(val);
                            this.currentOrder.apply_pos_order_discount_total();
                        } else {
                            super._setValue(val);
                            this.currentOrder.apply_pos_order_discount_total();
                        }
                    } else {
                        if (selectedLine && await selectedLine.get_promotion()) {
                            return false;
                        } else {
                            super._setValue(val);
                            this.currentOrder.apply_pos_promotion();
                            this.currentOrder.apply_pos_order_discount_total();
                        }
                    }
                    if (this.currentOrder && this.currentOrder.get_order_total_discount()) {
                        let promotion = this.currentOrder.get_order_total_discount();
                        if (promotion.total_amount > this.currentOrder.get_total_with_tax()) {
                            let removeLine = this.currentOrder.get_order_total_discount_line()
                            this.currentOrder.remove_orderline(removeLine)
                        }
                    }
                } else {
                    super._setValue(val);
                }
            }

            get_orderlines_from_order(line_ids) {
                var self = this;
                var orderLines = [];
                return new Promise(function (resolve, reject) {
                    rpc.query({
                        model: 'pos.order.line',
                        method: 'pos_order_line_read',
                        args: [this, line_ids],
                    }).then(function (order_lines) {
                        resolve(order_lines);
                    })
                });
            }

            get client() {
                return this.env.pos.get_client();
            }
            async _onClickPay() {
                let currentOrder = this.env.pos.get_order();
                var has_valid_product_lot = _.every(currentOrder.orderlines.models, function (line) {
                    return line.has_valid_product_lot();
                });
                if (!has_valid_product_lot) {
                    if (this.env.pos.config.restrict_lot_serial) {
                        const {confirmed} = await this.showPopup('ConfirmPopup', {
                            title: this.env._t('Empty Serial/Lot Number'),
                            body: this.env._t('One or more product(s) required serial/lot number !!'),
                        });
                        if (confirmed) {
                            return;
                        }
                    } else {
                        const {confirmed} = await this.showPopup('ConfirmPopup', {
                            title: this.env._t('Confirmation'),
                            body: this.env._t('Are you sure you want to continue ?'),
                        });
                        if (confirmed) {
                            this.showScreen('PaymentScreen');
                        }
                    }
                } else {
                    this.showScreen('PaymentScreen');
                }
            }

            async _clickProduct(event) {
                if (!this.env.pos.get_order().get_refund_order()) {
                    if (!this.currentOrder) {
                        this.env.pos.add_new_order();
                    }
                    const product = event.detail;
                    let price_extra = 0.0;
                    let draftPackLotLines, weight, description, packLotLinesToEdit;

                    if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                        let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                            .filter((attr) => attr !== undefined);
                        let {confirmed, payload} = await this.showPopup('ProductConfiguratorPopup', {
                            product: product,
                            attributes: attributes,
                        });

                        if (confirmed) {
                            description = payload.selected_attributes.join(', ');
                            price_extra += payload.price_extra;
                        } else {
                            return;
                        }
                    }

                    // Gather lot information if required.

                    if (['serial', 'lot'].includes(product.tracking)) {
                        const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                        if (isAllowOnlyOneLot) {
                            packLotLinesToEdit = [];
                        } else {
                            var orderline = this.currentOrder
                                .get_orderlines()
                                .filter(line => !line.get_discount())
                                .find(line => line.product.id === product.id);
                            if (orderline) {
                                packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                            } else {
                                packLotLinesToEdit = [];
                            }
                        }
                        if (this.env.pos.config.enable_pos_serial) {
                            var self = this;
                            var utcMoment = moment.utc();
                            var picking_type = this.env.pos.config.picking_type_id[0]
                            // this.product_lot_and_serial_number(product.id, isAllowOnlyOneLot)   
                            try {
                                var params = {
                                    model: 'stock.production.lot',
                                    method: 'product_lot_and_serial',
                                    args: [product, product.id, picking_type]
                                }
                                await rpc.query(params).then(async function (serials) {
                                    if (serials) {
                                        for (var i = 0; i < serials.length; i++) {
                                            if (serials[i].remaining_qty > 0) {
                                                serials[i]['isSelected'] = false;
                                                serials[i]['inputQty'] = 1;
                                                if (serials[i].expiration_date) {
                                                    let localTime = moment.utc(serials[i].expiration_date).toDate();
                                                    serials[i]['expiration_date'] = moment(localTime).format('YYYY-MM-DD hh:mm A');
                                                }
                                                if (self.env.pos.config.product_exp_days) {
                                                    let product_exp_date = moment().add(self.env.pos.config.product_exp_days, 'd')
                                                        .format('YYYY-MM-DD');
                                                    let serial_life = moment(serials[i]['expiration_date']).format('YYYY-MM-DD');
                                                    if (product_exp_date >= serial_life) {
                                                        serials[i]['NearToExpire'] = 'NearToExpire';
                                                     }
                                                }
                                                self.state.serials.push(serials[i])
                                            }
                                        }
                                        self.state.serials.sort(function (a, b) {
                                            return (b.expiration_date) - (a.expiration_date);
                                        });
                                        self.showScreen('PackLotLineScreen', {
                                            isSingleItem: isAllowOnlyOneLot,
                                            serials: self.state.serials
                                        });
                                    }
                                });
                            } catch (error) {
                                if (isRpcError(error) && error.message.code < 0) {
                                    self.env.pos.get_order().set_connected(false)
                                    const {confirmed, payload} = await this.showPopup('EditListPopup', {
                                        title: this.env._t('Lot/Serial Number(s) Required'),
                                        isSingleItem: isAllowOnlyOneLot,
                                        array: packLotLinesToEdit,
                                    });
                                    if (confirmed) {
                                        // Segregate the old and new packlot lines
                                        const modifiedPackLotLines = Object.fromEntries(
                                            payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                                        );
                                        const newPackLotLines = payload.newArray
                                            .filter(item => !item.id)
                                            .map(item => ({lot_name: item.text}));
                                        draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                                    } else {
                                        // We don't proceed on adding product.
                                        return;
                                    }
                                } else {
                                    throw error;
                                }
                            }
                        } else {
                            const {confirmed, payload} = await this.showPopup('EditListPopup', {
                                title: this.env._t('Lot/Serial Number(s) Required'),
                                isSingleItem: isAllowOnlyOneLot,
                                array: packLotLinesToEdit,
                            });
                            if (confirmed) {
                                // Segregate the old and new packlot lines
                                const modifiedPackLotLines = Object.fromEntries(
                                    payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                                );
                                const newPackLotLines = payload.newArray
                                    .filter(item => !item.id)
                                    .map(item => ({lot_name: item.text}));
                                draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                            } else {
                                // We don't proceed on adding product.
                                return;
                            }
                        }
                    }

                    // Take the weight if necessary.
                    if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                        // Show the ScaleScreen to weigh the product.
                        if (this.isScaleAvailable) {
                            const {confirmed, payload} = await this.showTempScreen('ScaleScreen', {
                                product,
                            });
                            if (confirmed) {
                                weight = payload.weight;
                            } else {
                                // do not add the product;
                                return;
                            }
                        } else {
                            await this._onScaleNotAvailable();
                        }
                    }
                    // Add the product after having the extra information.
                    this.currentOrder.add_product(product, {
                        draftPackLotLines,
                        description: description,
                        price_extra: price_extra,
                        quantity: weight,
                    });
                    this.currentOrder.get_selected_orderline().set_serials(this.state.serials)
                    NumberBuffer.reset();
                } else {
                    return false
                }
            }

            async _barcodeProductAction(code) {
                const product = this.env.pos.db.get_product_by_barcode(code.base_code)
                if (!product) {
                    return this._barcodeErrorAction(code);
                }
                if (!this.env.pos.get_order().get_refund_order()) {
                    if (!this.currentOrder) {
                        this.env.pos.add_new_order();
                    }
                    let price_extra = 0.0;
                    let draftPackLotLines, weight, description, packLotLinesToEdit;

                    if (this.env.pos.config.product_configurator && _.some(product.attribute_line_ids, (id) => id in this.env.pos.attributes_by_ptal_id)) {
                        let attributes = _.map(product.attribute_line_ids, (id) => this.env.pos.attributes_by_ptal_id[id])
                            .filter((attr) => attr !== undefined);
                        let {confirmed, payload} = await this.showPopup('ProductConfiguratorPopup', {
                            product: product,
                            attributes: attributes,
                        });

                        if (confirmed) {
                            description = payload.selected_attributes.join(', ');
                            price_extra += payload.price_extra;
                        } else {
                            return;
                        }
                    }

                    // Gather lot information if required.

                    if (['serial', 'lot'].includes(product.tracking)) {
                        const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                        if (isAllowOnlyOneLot) {
                            packLotLinesToEdit = [];
                        } else {
                            var orderline = this.currentOrder
                                .get_orderlines()
                                .filter(line => !line.get_discount())
                                .find(line => line.product.id === product.id);
                            if (orderline) {
                                packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                            } else {
                                packLotLinesToEdit = [];
                            }
                        }
                        if (this.env.pos.config.enable_pos_serial) {
                            var self = this;
                            var utcMoment = moment.utc();
                            var picking_type = this.env.pos.config.picking_type_id[0]
                            // this.product_lot_and_serial_number(product.id, isAllowOnlyOneLot)
                            try {
                                var params = {
                                    model: 'stock.production.lot',
                                    method: 'product_lot_and_serial',
                                    args: [product, product.id, picking_type]
                                }
                                await rpc.query(params).then(async function (serials) {
                                    if (serials) {
                                        for (var i = 0; i < serials.length; i++) {
                                            if (serials[i].remaining_qty > 0) {
                                                serials[i]['isSelected'] = false;
                                                serials[i]['inputQty'] = 1;
                                                if (serials[i].expiration_date) {
                                                    let localTime = moment.utc(serials[i].expiration_date).toDate();
                                                    serials[i]['expiration_date'] = moment(localTime).format('YYYY-MM-DD hh:mm A');
                                                }
                                                if (self.env.pos.config.product_exp_days) {
                                                    let product_exp_date = moment().add(self.env.pos.config.product_exp_days, 'd')
                                                        .format('YYYY-MM-DD');
                                                    let serial_life = moment(serials[i]['expiration_date']).format('YYYY-MM-DD');
                                                    if (product_exp_date >= serial_life) {
                                                        serials[i]['NearToExpire'] = 'NearToExpire';
                                                    }
                                                }
                                                self.state.serials.push(serials[i])
                                            }
                                        }
                                        self.state.serials.sort(function (a, b) {
                                            return (b.expiration_date) - (a.expiration_date);
                                        });
                                        self.showScreen('PackLotLineScreen', {
                                            isSingleItem: isAllowOnlyOneLot,
                                            serials: self.state.serials
                                        });
                                    }
                                });
                            } catch (error) {
                                if (isRpcError(error) && error.message.code < 0) {
                                    self.env.pos.get_order().set_connected(false)
                                    const {confirmed, payload} = await this.showPopup('EditListPopup', {
                                        title: this.env._t('Lot/Serial Number(s) Required'),
                                        isSingleItem: isAllowOnlyOneLot,
                                        array: packLotLinesToEdit,
                                    });
                                    if (confirmed) {
                                        // Segregate the old and new packlot lines
                                        const modifiedPackLotLines = Object.fromEntries(
                                            payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                                        );
                                        const newPackLotLines = payload.newArray
                                            .filter(item => !item.id)
                                            .map(item => ({lot_name: item.text}));
                                        draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                                    } else {
                                        // We don't proceed on adding product.
                                        return;
                                    }
                                } else {
                                    throw error;
                                }
                            }
                        } else {
                            const {confirmed, payload} = await this.showPopup('EditListPopup', {
                                title: this.env._t('Lot/Serial Number(s) Required'),
                                isSingleItem: isAllowOnlyOneLot,
                                array: packLotLinesToEdit,
                            });
                            if (confirmed) {
                                // Segregate the old and new packlot lines
                                const modifiedPackLotLines = Object.fromEntries(
                                    payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                                );
                                const newPackLotLines = payload.newArray
                                    .filter(item => !item.id)
                                    .map(item => ({lot_name: item.text}));
                                draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                            } else {
                                // We don't proceed on adding product.
                                return;
                            }
                        }
                    }

                    // Take the weight if necessary.
                    if (product.to_weight && this.env.pos.config.iface_electronic_scale) {
                        // Show the ScaleScreen to weigh the product.
                        if (this.isScaleAvailable) {
                            const {confirmed, payload} = await this.showTempScreen('ScaleScreen', {
                                product,
                            });
                            if (confirmed) {
                                weight = payload.weight;
                            } else {
                                // do not add the product;
                                return;
                            }
                        } else {
                            await this._onScaleNotAvailable();
                        }
                    }
                    // Add the product after having the extra information.
                    this.currentOrder.add_product(product, {
                        draftPackLotLines,
                        description: description,
                        price_extra: price_extra,
                        quantity: weight,
                    });
                    this.currentOrder.get_selected_orderline().set_serials(this.state.serials)
                    NumberBuffer.reset();
                } else {
                    return false
                }
            }

            is_packaging_product(event) {
                if (this.state.warehouse_mode) {
                    this.state.warehouse_mode = false;
                }
                if (this.state.alternate_product) {
                    this.state.alternate_product = false;
                }
                if (this.state.cross_selling_product) {
                    this.state.cross_selling_product = false;
                }
                if (this.state.isPackaging === false) {
                    this.state.isPackaging = true
                    this.env.pos.set('selectedCategoryId', 0);
                } else {
                    this.state.isPackaging = false
                }
                this.props.products = event.detail
            }

            get productsToDisplay() {
                return this.props.products
                // super.productsToDisplay
            }

            CrossSellingProduct() {
                if (this.state.warehouse_mode) {
                    this.state.warehouse_mode = false;
                }
                if (this.state.alternate_product) {
                    this.state.alternate_product = false;
                }
                if (this.state.cross_selling_product) {
                    this.state.cross_selling_product = false;
                }
                if (this.currentOrder.get_selected_orderline()) {
                    this.state.cross_selling_product = true;
                    var product = this.env.pos.get_order().get_selected_orderline().product
                    this.state.line_product = this.env.pos.get_order().get_selected_orderline().product
                } else {
                    alert('Please Select Product.');
                }
            }

            ClickAlternateProduct() {
                if (this.state.warehouse_mode) {
                    this.state.warehouse_mode = false;
                }
                if (this.state.alternate_product) {
                    this.state.alternate_product = false;
                }
                if (this.state.cross_selling_product) {
                    this.state.cross_selling_product = false;
                }
                if (this.currentOrder.get_selected_orderline()) {
                    this.state.alternate_product = true;
                    var product = this.env.pos.get_order().get_selected_orderline().product
                    this.state.line_product = this.env.pos.get_order().get_selected_orderline().product
                } else {
                    alert('Please Select Product.');
                }

            }

            _onButtonClick() {
                if (this.state.warehouse_mode) {
                    this.state.warehouse_mode = false;
                }
                if (this.state.alternate_product) {
                    this.state.alternate_product = false;
                }
                if (this.state.cross_selling_product) {
                    this.state.cross_selling_product = false;
                }
                if (this.currentOrder.get_selected_orderline()) {
                    this.state.warehouse_mode = true;
                    this._createData();
                } else {
                    alert('Please Select Product.');
                }
            }

            _closeWarehouse() {
                if (this.state.warehouse_mode) {
                    this.state.warehouse_mode = false;
                }
                if (this.state.alternate_product) {
                    this.state.alternate_product = false;
                }
                if (this.state.cross_selling_product) {
                    this.state.cross_selling_product = false;
                }
            }

            _changeWarehouseProduct(event) {
                if (this.state.warehouse_mode) {
                    this._createData();
                }
                if (this.state.alternate_product) {
                    this.state.line_product = this.env.pos.get_order().get_selected_orderline().product
                }
                if (this.state.cross_selling_product) {
                    this.state.line_product = this.env.pos.get_order().get_selected_orderline().product
                }
            }

            _createData() {
                var self = this;
                var product = this.currentOrder.get_selected_orderline().product;
                if (product) {
                    var QtyGetPromise = new Promise(function (resolve, reject) {
                        rpc.query({
                            model: 'stock.warehouse',
                            method: 'display_prod_stock',
                            args: [product.id]
                        }).then(function (result) {
                            if (result) {
                                resolve(result);
                            } else {
                                reject()
                            }
                        });
                    });
                    QtyGetPromise.then(function (res) {
                        self.state.warehouseData = res;
                        self.state.title = product.display_name;
                    });
                }
            }

            _showWarehouseReceipt() {
                this.showScreen('ReceiptScreen', {
                    'check': 'from_warehouse',
                    'receiptData': this.state.warehouseData,
                    'productName': this.state.title
                });
            }
        }

    Registries.Component.extend(ProductScreen, AsplRetProductScreenInh);

    return ProductScreen;

});
