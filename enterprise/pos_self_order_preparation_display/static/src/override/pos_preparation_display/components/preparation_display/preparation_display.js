import { patch } from "@web/core/utils/patch";
import { PreparationDisplay } from "@pos_preparation_display/app/components/preparation_display/preparation_display";
import { useService } from "@web/core/utils/hooks";

patch(PreparationDisplay.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state.isAlertMenu = false;
    },
    get outOfPaperListFiltered() {
        const outOfPaperList = this.preparationDisplay.configPaperStatus;
        return outOfPaperList.filter((outOfPaperList) => !outOfPaperList.has_paper);
    },
    closeAlertMenu() {
        this.state.isAlertMenu = false;
    },
    openAlertMenu() {
        this.state.isAlertMenu = true;
    },
    async paperNotificationClick(configPaperStatus) {
        configPaperStatus.has_paper = !configPaperStatus.has_paper;
        await this.orm.call(
            "pos_preparation_display.display",
            "change_paper_status",
            [configPaperStatus.id, configPaperStatus.has_paper],
            {}
        );
    },
});
