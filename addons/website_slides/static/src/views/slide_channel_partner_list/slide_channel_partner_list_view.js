/** @odoo-module **/

import { listView } from '@web/views/list/list_view';
import { registry } from '@web/core/registry';

import SlideChannelPartnerListController from './slide_channel_partner_list_controller.js';

export const SlideChannelPartnerListView = {
    ...listView,
    Controller: SlideChannelPartnerListController,
    buttonTemplate: 'website_slides.SlideChannelPartnerListView.buttons',
};

registry.category('views').add('slide_channel_partner_enroll_tree', SlideChannelPartnerListView);
