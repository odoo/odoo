odoo.define('pos_hr.chrome', function (require) {
    'use strict';

    const Chrome = require('point_of_sale.Chrome');
    const Registries = require('point_of_sale.Registries');
    const useSelectEmployee = require('pos_hr.useSelectEmployee');

    const PosHrChrome = (Chrome) =>
        class extends Chrome {
            async start() {
                await super.start();
                if (this.env.pos.config.module_pos_hr) {
                    this.env.pos.on('change:cashier', this.render, this);
                }
                const { selectEmployee } = useSelectEmployee();
                let successfulInitialLogin = false;
                setTimeout(async () => {
                    const list = this.env.pos.employees.map((employee) => {
                        return {
                            id: employee.id,
                            item: employee,
                            label: employee.name,
                            isSelected: false,
                            barcode: employee.barcode,
                        };
                    });
                    while (!successfulInitialLogin) {
                        const selectedEmployee = await selectEmployee(list, { hideCancelButton: true });
                        if (selectedEmployee) {
                            successfulInitialLogin = true;
                            this.env.pos.set_cashier(selectedEmployee);
                        }
                    }
                });
            }
            get headerButtonIsShown() {
                if (this.env.pos.config.module_pos_hr) {
                    const currentCashier = this.env.pos.get_cashier();
                    return (
                        currentCashier.user_id[0] === this.env.pos.session.uid ||
                        currentCashier.role === 'manager'
                    );
                } else {
                    return true;
                }
            }
        };

    Registries.Component.extend(Chrome, PosHrChrome);

    return Chrome;
});
