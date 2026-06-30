/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const exampleData = {
    ghostColumns: [_t('Ideas'), _t('Design'), _t('Review'), _t('Send'), _t('Done')],
    applyExamplesText: _t("Use This For My Campaigns"),
    allowedGroupBys: ['stage_id'],
    examples: [{
        name: _t('Creative Flow'),
        columns: [_t('Ideas'), _t('Design'), _t('Review'), _t('Send'), _t('Done')],
        description: _t("Collect ideas, design creative content and publish it once reviewed."),
    }, {
        name: _t('Event-driven Flow'),
        columns: [_t('Later'), _t('This Month'), _t('This Week'), _t('Running'), _t('Sent')],
        description: _t("Track incoming events (e.g. Christmas, Black Friday, ...) and publish timely content."),
    }, {
        name: _t('Soft-Launch Flow'),
        columns: [_t('Pre-Launch'), _t('Soft-Launch'), _t('Deploy'), _t('Report'), _t('Done')],
        description: _t("Prepare your Campaign, test it with part of your audience and deploy it fully afterwards."),
    }, {
        name: _t('Audience-driven Flow'),
        columns: [_t('Gather Data'), _t('List-Building'), _t('Copywriting'), _t('Sent')],
        description: _t("Gather data, build a recipient list and write content based on your Marketing target."),
    }, {
        name: _t('Approval-based Flow'),
        columns: [_t('To be Approved'), _t('Approved'), _t('Deployed')],
        description: _t("Prepare Campaigns and get them approved before making them go live."),
    }],
};

registry.category("kanban_examples").add("utm_campaign", exampleData);
