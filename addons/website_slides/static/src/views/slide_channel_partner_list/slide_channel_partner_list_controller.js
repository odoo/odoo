/** @odoo-module native */
import { useService } from "@web/core/utils/hooks";
import { ListController } from "@web/views/list";

export default class SlideChannelPartnerListController extends ListController {
    static template = "website_slides.SlideChannelPartnerListView";
    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        this.channelId = this.props.context.default_channel_id || false;
    }

    /**
     * @private
     */
    async _openEnrollWizard() {
        const action = await this.orm.call("slide.channel", "action_channel_enroll", [
            this.channelId,
        ]);
        this.action.doAction(action, {
            onClose: async () => {
                await this.model.load();
                this.model.useSampleModel = false;
            },
        });
    }
}
