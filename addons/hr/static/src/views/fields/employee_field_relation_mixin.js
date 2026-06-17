import { AvatarCard } from "@mail/core/web/avatar_card/avatar_card";
import { onWillStart, props, t } from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { user } from "@web/core/user";

/**
 * Mixin that handles public/private access of employee records in many2X fields
 * @param { Class } fieldClass
 * @param { Object } parentProps the props schema of `fieldClass`
 * @returns Class
 */
export function EmployeeFieldRelationMixin(fieldClass, parentProps) {
    return class extends fieldClass {
        props = props({
            ...parentProps,
            relation: t.string().optional(),
        });

        setup() {
            super.setup();
            onWillStart(async () => {
                this.isHrUser = await user.hasGroup("hr.group_hr_user");
            });
            this.avatarCard = usePopover(AvatarCard, { closeOnClickAway: true });
        }

        get relation() {
            if (this.props.relation) {
                return this.props.relation;
            }
            return this.isHrUser ? "hr.employee" : "hr.employee.public";
        }
    };
}
