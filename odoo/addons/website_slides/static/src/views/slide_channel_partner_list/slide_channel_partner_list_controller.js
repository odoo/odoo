/** @odoo-module **/

import { ListController } from '@web/views/list/list_controller';
import { useService } from '@web/core/utils/hooks';


export default class SlideChannelPartnerListController extends ListController {
    setup() {
        super.setup();
        this.action = useService('action');
        this.orm = useService('orm');
        this.channelId = this.props.context.default_channel_id || false;
    }

    /**
     * Method opening the wizard to enroll new slide channel partners.
     * Reloads the model afterwards to see new attendees.
     * 
     * @private
     */
    async _openEnrollWizard() {
        const action = await this.orm.call(
            'slide.channel',
            'action_channel_enroll',
            [this.channelId]
        );
        this.action.doAction(action, {
            onClose: async () => {
                await this.model.load();
                this.model.useSampleModel = false;
                this.render(true);
            }
        });
    }
}
SlideChannelPartnerListController.template = "website_slides.SlideChannelPartnerListView";
