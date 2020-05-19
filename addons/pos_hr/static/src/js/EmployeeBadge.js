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
            this.state = useState({ isMouseOver: false });
        }
        mounted() {
            this.env.pos.on('change:cashier', this.render, this);
        }
        willUnmount() {
            this.env.pos.off('change:cashier', null, this);
        }
        get cashier() {
            return this.env.pos.get_cashier();
        }
        get text() {
            if (this.state.isMouseOver) {
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
                .filter((employee) => employee.id !== this.cashier.id)
                .map((employee) => {
                    return {
                        id: employee.id,
                        item: employee,
                        label: employee.name,
                        isSelected: false,
                    };
                });

            const employee = await this.selectEmployee(list);
            if (employee) {
                this.env.pos.set_cashier(employee);
            }
        }
    }
    EmployeeBadge.template = 'EmployeeBadge';

    Registries.Component.add(EmployeeBadge);

    return EmployeeBadge;
});
