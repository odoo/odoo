odoo.define('pos_restaurant.Orderline', function(require) {
    'use strict';

    const Orderline = require('point_of_sale.Orderline');
    const Registries = require('point_of_sale.Registries');
    const { useListener } = require("@web/core/utils/hooks");

    const PosResOrderline = Orderline =>
        class extends Orderline {
            setup() {
                super.setup();
                useListener('click-internal-note', this.onClickInternalNote);
            }
            /**
             * @override
             */
            get addedClasses() {
                const res = super.addedClasses;
                Object.assign(res, {
                    dirty: this.props.line.mp_dirty,
                    skip: this.props.line.mp_skip,
                });
                return res;
            }
            /**
             * @override
             * if doubleclick, change mp_dirty to mp_skip
             *
             * IMPROVEMENT: Instead of handling both double click and click in single
             * method, perhaps we can separate double click from single click.
             */
            selectLine() {
                const line = this.props.line; // the orderline
                if (this.env.pos.get_order().selected_orderline.id !== line.id) {
                    this.mp_dbclk_time = new Date().getTime();
                } else if (!this.mp_dbclk_time) {
                    this.mp_dbclk_time = new Date().getTime();
                } else if (this.mp_dbclk_time + 500 > new Date().getTime()) {
                    line.set_skip(!line.mp_skip);
                    this.mp_dbclk_time = 0;
                } else {
                    this.mp_dbclk_time = new Date().getTime();
                }
                super.selectLine();
            }
            async onClickInternalNote() {
                const selectedOrderline = this.env.pos.get_order().get_selected_orderline();
                const { confirmed, payload: inputNote } = await this.showPopup('TextAreaPopup', {
                    startingValue: selectedOrderline.get_note(),
                    title: this.env._t('Add Internal Note'),
                });

                if (confirmed) {
                    selectedOrderline.set_note(inputNote);
                }
            }
        };

    Registries.Component.extend(Orderline, PosResOrderline);

    return Orderline;
});
