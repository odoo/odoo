odoo.define('aumet_pos_flexipharmacy_fix.ProductScreen', function (require) {
        'use strict';

        const PosComponent = require('point_of_sale.PosComponent');
        const ProductScreen = require('flexipharmacy.ProductScreen');
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
                }

                async _barcodeProductAction(code) {
                    const product = this.env.pos.db.get_product_by_barcode(code.base_code)
                    if (!product) {
                        return this._barcodeErrorAction(code);
                    }
                    if (!this.currentOrder) {
                        this.env.pos.add_new_order();
                    }
                    const options = await this._getAddProductLotUOM(product);
                    // Do not add product if options is undefined.
                    if (!options['draftPackLotLines']) return;
                    // Add the product after having the extra information.
                    this.currentOrder.add_product(product, options);
                    NumberBuffer.reset();
                }

                async _getAddProductLotUOM(product) {
                    let price_extra = 0.0;
                    let draftPackLotLines, weight, description, packLotLinesToEdit, lst_price, selected_uom;

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
                    if (['serial', 'lot'].includes(product.tracking) && (this.env.pos.picking_type.use_create_lots || this.env.pos.picking_type.use_existing_lots)) {
                        const isAllowOnlyOneLot = product.isAllowOnlyOneLot();
                        if (isAllowOnlyOneLot) {
                            packLotLinesToEdit = [];
                        } else {
                            const orderline = this.currentOrder
                                .get_orderlines()
                                .filter(line => !line.get_discount())
                                .find(line => line.product.id === product.id);
                            if (orderline) {
                                packLotLinesToEdit = orderline.getPackLotLinesToEdit();
                            } else {
                                packLotLinesToEdit = [];
                            }
                        }
                        var self = this;
                        var utcMoment = moment.utc();
                        var picking_type = this.env.pos.config.picking_type_id[0]

                        try {
                            var params = {
                                model: 'stock.production.lot',
                                method: 'product_lot_and_serial',
                                args: [product, product.id, picking_type]
                            }
                            await rpc.query(params).then(async function (serials) {
                                if (serials) {
                                    self.state.uom_list = [];
                                    let custom_price = product.pos.product_uom_price[product.product_tmpl_id];
                                    let product_uom_category = self.env.pos.units.filter(item => item.id == product.uom_id[0])[0];

                                    self.state.serials = []
                                    for (var i = 0; i < serials.length; i++) {
                                        if (serials[i].product_qty != 0) {
                                            if (serials[i].expiration_date) {
                                                let localTime = moment.utc(serials[i].expiration_date).toDate();
                                                serials[i]['expiration_date'] = moment(localTime).format('YYYY-MM-DD');
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
                                    if (self.state.serials.length > 0) {
                                        self.state.serials[0]['isSelected'] = true;
                                    } else {
                                        alert("The requested qty is not available");
                                        return
                                    }
                                    for (var uom in self.env.pos.units) {
                                        if (self.env.pos.units[uom].category_id[0] == product_uom_category.category_id[0]) {
                                            let price = (self.env.pos.units[uom].factor_inv * product.lst_price).toFixed(3);
                                            if (custom_price) {
                                                if (custom_price.uom_id[self.env.pos.units[uom].id]) {
                                                    price = custom_price.uom_id[self.env.pos.units[uom].id].price;
                                                }
                                            }

                                            self.state.uom_list.push({
                                                id: self.env.pos.units[uom].id,
                                                label: self.env.pos.units[uom].name,
                                                factor_inv: self.env.pos.units[uom].factor_inv.toFixed(3),
                                                item: self.env.pos.units[uom],
                                                price: price,
                                                qty: parseInt(self.state.serials[0].product_qty / self.env.pos.units[uom].factor_inv)
                                            });
                                        }
                                    }
                                    self.state.serials.sort(function (a, b) {
                                        return (b.expiration_date) - (a.expiration_date);
                                    });
                                    const {confirmed, payload} = await self.showPopup('EditListPopup', {
                                        title: self.env._t('Lot/Serial Number(s) Required'),
                                        isSingleItem: isAllowOnlyOneLot,
                                        serials: self.state.serials,
                                        uom_list: self.state.uom_list
                                    });
                                    if (confirmed) {
                                        selected_uom = payload.selected_uom;
                                        lst_price = self.state.uom_list.filter(item => item.id == payload.selected_uom[0])[0].price;
                                        // Segregate the old and new packlot lines
                                        const modifiedPackLotLines = Object.fromEntries(
                                            payload.newArray.filter(item => item.id).map(item => [item.id, item.text])
                                        );
                                        const newPackLotLines = payload.newArray
                                            .filter(item => !item.id)
                                            .map(item => ({lot_name: item.text}));

                                        draftPackLotLines = {modifiedPackLotLines, newPackLotLines};
                                    } else {
                                        return;
                                    }

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

                    return {
                        draftPackLotLines,
                        quantity: weight,
                        description,
                        price_extra,
                        selected_price: lst_price,
                        selected_uom: selected_uom
                    };
                }

                async _clickProduct(event) {
                    if (!this.currentOrder) {
                        this.env.pos.add_new_order();
                    }
                    const product = event.detail;
                    let options;
                    if (product.tracking == 'lot') {

                        options = await this._getAddProductLotUOM(product);

                        // Do not add product if options is undefined.
                        if (!options['draftPackLotLines']) return;
                        this.currentOrder.add_product(product, options);
                        this.currentOrder.selected_orderline.price = options['selected_price'];
                        this.currentOrder.selected_orderline.uom_id = options['selected_uom'];

                        NumberBuffer.reset();
                    } else {
                        options = await this._getAddProductOptions(product);
                        // Do not add product if options is undefined.
                        if (!options) return;
                        this.currentOrder.add_product(product, options);
                        NumberBuffer.reset();
                    }

                }


            }

        Registries.Component.extend(ProductScreen, AsplRetProductScreenInh);

        return ProductScreen;

    }
)
;
