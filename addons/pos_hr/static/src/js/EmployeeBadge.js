odoo.define('pos_hr.EmployeeBadge', function (require) {
    'use strict';

    const Registries = require('point_of_sale.Registries');
    const PosComponent = require('point_of_sale.PosComponent');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');
    const { useListener } = require('web.custom_hooks');
    const { useState } = owl.hooks;

    class EmployeeBadge extends PosComponent {
        constructor() {
            super(...arguments);
            const { selectEmployee } = useSelectEmployee();
            this.selectEmployee = selectEmployee;
            useListener('click', this._selectCashier);
            this.state = useState({ isMouseEnter: false });
            // We use the following state variables to assure the following behavior:
            //  When the mouse pointer enters this component's element, the element's
            //  width is set to whichever width is larger when the text is 'Select User'
            //  vs when the text is '<Employee name>'.
            this._widthBeforeMouseEnter = 0;
            this._usePreviousWidth = false;
        }
        mounted() {
            this.env.pos.on('change:cashier', this.render, this);
        }
        willUnmount() {
            this.env.pos.off('change:cashier', null, this);
        }
        willPatch() {
            if (this._usePreviousWidth) {
                this._widthBeforeMouseEnter = getComputedStyle(this.el).getPropertyValue(
                    'width'
                );
            }
        }
        patched() {
            if (this._usePreviousWidth) {
                const newWidth = getComputedStyle(this.el).getPropertyValue('width');
                if (parseFloat(newWidth) < parseFloat(this._widthBeforeMouseEnter)) {
                    this.el.style.width = this._widthBeforeMouseEnter;
                }
                this._usePreviousWidth = false;
            } else {
                this.el.style.width = 'auto';
            }
        }
        get cashier() {
            return this.env.pos.get_cashier();
        }
        get text() {
            if (this.state.isMouseEnter) {
                return this._onMouseOverText();
            } else {
                return this.cashier ? this.cashier.name : '';
            }
        }
        _onMouseOverText() {
            return this.env._t('Select User');
        }
        async _selectCashier() {
            if (!this.env.pos.config.module_pos_hr) return;

            const list = this.env.pos.employees
                .map((employee) => {
                    return {
                        id: employee.id,
                        item: employee,
                        label: employee.name,
                        isSelected: this.cashier.id == employee.id,
                        barcode: employee.barcode,
                    };
                });

            const employee = await this.selectEmployee(list);
            if (employee) {
                this.env.pos.set_cashier(employee);
            }
        }
        onMouseEnter() {
            this._usePreviousWidth = true;
            this.state.isMouseEnter = true;
        }
        onMouseLeave() {
            this.state.isMouseEnter = false;
        }
    }
    EmployeeBadge.template = 'EmployeeBadge';

    Registries.Component.add(EmployeeBadge);

    return EmployeeBadge;
});
