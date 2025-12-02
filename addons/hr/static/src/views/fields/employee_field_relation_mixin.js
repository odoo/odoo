import { AvatarCardEmployeePopover } from "@hr/components/avatar_card_employee/avatar_card_employee_popover";
import { onWillStart } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { user } from "@web/core/user";

/**
 * Mixin that handles public/private access of employee records in many2X fields
 * @param { Class } fieldClass
 * @returns Class
 */
export function EmployeeFieldRelationMixin(fieldClass) {
    return class extends fieldClass {
        static props = {
            ...fieldClass.props,
            relation: { type: String, optional: true },
        };

        setup() {
            super.setup();
            onWillStart(async () => {
                this.isHrUser = await user.hasGroup("hr.group_hr_user");
            });
            this.avatarCard = usePopover(AvatarCardEmployeePopover, { closeOnClickAway: true });
        }

        get relation() {
            if (this.props.relation) {
                return this.props.relation;
            }
            return this.isHrUser ? "hr.employee" : "hr.employee.public";
        }

        getAvatarCardProps(record) {
            const originalProps = super.getAvatarCardProps(record);
            if (["hr.employee", "hr.employee.public"].includes(this.relation)) {
                return {
                    ...originalProps,
                    recordModel: this.relation,
                };
            }
            return originalProps;
        }
    };
}
