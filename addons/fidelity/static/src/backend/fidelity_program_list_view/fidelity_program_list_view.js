import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { registry } from "@web/core/registry";
import { onWillStart, useState, onWillRender, useRef, useEffect } from "@odoo/owl";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { useTrackedAsync } from "../utils";
import { ListRenderer } from "@web/views/list/list_renderer";
import { ListController } from "@web/views/list/list_controller";
import { listView } from "@web/views/list/list_view";

async function updateFidelityProgramListViewState(orm, stateObj) {
    const result = await orm.call("fidelity.program", "get_fidelity_program_list_view_state");
    Object.assign(stateObj, result);
}

export class FidelityProgramListController extends ListController {
    static template = "fidelity.FidelityProgramListController";
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.initialState = {
            has_records: true,
            show_predefined_programs: true,
        };

        onWillStart(() => updateFidelityProgramListViewState(this.orm, this.initialState));
    }
}

export class FidelityProgramListRenderer extends ListRenderer {
    static template = "fidelity.FidelityProgramListRenderer";
    static props = [...ListRenderer.props, "initialState"];

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState(this.props.initialState);
        this.tableRef = useRef("table");
        this.loadProgram = useTrackedAsync(
            async ({ type }) =>
                await this.callWithViewUpdate(async () => {
                    const result = await this.orm.call(
                        "fidelity.program",
                        "create_default_fidelity_program",
                        [type]
                    );
                    return result;
                })
        );

        onWillRender(() => (this.state.show_predefined_programs = this.props.list.count === 0));

        useEffect(
            () => {
                if (!this.tableRef?.el) {
                    return;
                }

                if (this.state.show_predefined_programs) {
                    this.tableRef.el.classList.add("d-none");
                } else {
                    this.tableRef.el.classList.remove("d-none");
                }
            },
            () => [this.tableRef.el, this.state.show_predefined_programs]
        );
    }

    async clickLoadProgram(item) {
        await this.loadProgram.call(item);
        if (this.loadProgram.status == "error") {
            throw this.loadProgram.result;
        }
    }

    async callWithViewUpdate(func) {
        try {
            const [isAdmin] = await Promise.all([user.hasGroup("base.group_system")]);

            if (!isAdmin) {
                this.dialog.add(AlertDialog, {
                    title: _t("Access Denied"),
                    body: _t("It seems like you do not have enough rights to create a program."),
                });
                return;
            }

            const result = await func();
            await updateFidelityProgramListViewState(this.orm, this.state);
            return result;
        } finally {
            this.env.searchModel.clearQuery();
        }
    }

    get availablePrograms() {
        return [
            {
                name: _t("Buy X get Y"),
                description: _t("Buy a certain number of products and get some for free"),
                type: "buy_x_get_y",
                iconFile: "2_plus_1.svg",
            },
            {
                name: _t("Fidelity Points"),
                description: _t("Fidelity program: collect points and get rewards"),
                type: "fidelity_points",
                iconFile: "loyalty_cards.svg",
            },
            {
                name: _t("Coupons & Promotions"),
                description: _t("Offer promotions on next orders"),
                type: "promotion",
                iconFile: "promo_code.svg",
            },
        ];
    }

    get showNoContentHelper() {
        return false;
    }
}

export const FidelityProgramListView = {
    ...listView,
    Renderer: FidelityProgramListRenderer,
    Controller: FidelityProgramListController,
};

registry.category("views").add("fidelity_program_list_view", FidelityProgramListView);
