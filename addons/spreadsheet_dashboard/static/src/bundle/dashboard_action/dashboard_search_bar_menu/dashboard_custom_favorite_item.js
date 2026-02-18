import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { CustomFavoriteItem } from "@web/search/custom_favorite_item/custom_favorite_item";

export class DashboardCustomFavoriteItem extends CustomFavoriteItem {
    static props = {
        ...CustomFavoriteItem.props,
        currentGlobalFilters: Object,
    };

    setup() {
        super.setup();
        this.actionService = useService("action");
        this.loader = useService("spreadsheet_dashboard_loader");
        this.searchModel = this.loader.getDashboard(this.loader.activeDashboardId).searchModel;
        this.state.description = this.loader.getDashboard(this.loader.activeDashboardId).data.name;
    }

    async saveFavorite(ev) {
        if (!this.state.description) {
            this.notificationService.add(_t("A name for your favorite filter is required."), {
                type: "danger",
            });
            ev.stopPropagation();
            this.descriptionRef.el.focus();
            return false;
        }
        const { description, isDefault } = this.state;
        const serverSideId = this.searchModel.createFavoriteRecord(
            description,
            isDefault,
            this.props.currentGlobalFilters
        );

        Object.assign(this.state, {
            description: this.loader.getDashboard(this.loader.activeDashboardId).data.name,
            isDefault: false,
        });
        return serverSideId;
    }

    async editFavorite(ev) {
        const serverSideId = await this.saveFavorite(ev);
        if (!serverSideId) {
            return;
        }
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "spreadsheet.dashboard.favorite.filters",
            views: [[false, "form"]],
            context: {
                form_view_ref:
                    "spreadsheet_dashboard.spreadsheet_dashboard_favorite_filters_view_edit_form",
            },
            res_id: serverSideId,
        });
    }
}
