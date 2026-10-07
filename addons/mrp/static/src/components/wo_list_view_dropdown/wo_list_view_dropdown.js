import { useProps, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { BadgeField, badgeField } from "@web/views/fields/badge/badge_field";
import { _t } from "@web/core/l10n/translation";

export class MOListViewDropdown extends BadgeField {
    static template = "mrp.MOViewListDropdown";
    static components = {
        Dropdown,
        DropdownItem,
    };

    props = useProps({
        ...standardFieldProps,
        display: t.string(),
        viewType: t.string().optional(),
    });

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.colorIcons = {
            "blocked": "o_status_warning",
            "progress": "o_status_info",
            "cancel": "o_status_danger",
            "done": "o_status_success",
        };
        this.icons = {
            "progress": "play_circle",
            "cancel": "cancel",
            "done": "check_circle",
        };
    }

    async reload(){
        await this.props.record.load();
        await this.env.model.root.load();
        this.env.model.notify();
    }

    get statusColor() {
        const state = this.props.record.data.state;
        return this.colorIcons[state] || "";
    }

    get statusIcon() {
        const state = this.props.record.data.state;
        return this.icons[state] || "circle";
    }

    async setState(state) {
        let selectedWorkorders = this.props.record.model.root.selection;
        if (!selectedWorkorders || selectedWorkorders.length == 0) {
            selectedWorkorders = [this.props.record];
        }
        let ids = selectedWorkorders.filter((wo) => wo.data.production_state != 'done').map((wo) => wo.resId)
        if (ids && ids.length > 0) {
            await this.callOrm("set_state", [state], ids);
        }
    }

    async callOrm(functionName, args, ids = undefined) {
        if (!ids){
            ids = this.props.record.model.root.selection?.map((element) => element.evalContext.id);
        }
        // if no records selected, take the current clicked one
        if (!ids || ids.length == 0) {
            ids = [this.props.record.resId];
        }
        let result;
        if (args !== undefined) {
            result = await this.orm.call("mrp.workorder", functionName, [ids, ...args]);
        } else {
            result = await this.orm.call("mrp.workorder", functionName, [ids]);
        }
        if (result && typeof result === "object") {
            return this.action.doAction(result, {
                onClose: async () => {
                    await this.reload();
                },
            });
        }
        await this.reload();
    }
};

registry.category("fields").add("mo_view_list_dropdown", {
    ...badgeField,
    supportedOptions: [
        {
            label: _t("Display"),
            name: "display",
            type: "String",
        },
    ],
    extractProps: ({ options, viewType }) => ({
        display: options.display,
        // Arch type where the <field> is declared (e.g. "list" for a one2many inside a form).
        viewType,
    }),
    component: MOListViewDropdown,
});
