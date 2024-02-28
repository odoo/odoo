odoo.define('utm.campaing_kanban_examples', function (require) {
'use strict';

var core = require('web.core');
var kanbanExamplesRegistry = require('web.kanban_examples_registry');
const { registry } = require("@web/core/registry");

var _lt = core._lt;

const exampleData = {
    ghostColumns: [_lt('Ideas'), _lt('Design'), _lt('Review'), _lt('Send'), _lt('Done')],
    applyExamplesText: _lt("Use This For My Campaigns"),
    allowedGroupBys: ['stage_id'],
    examples: [{
        name: _lt('Creative Flow'),
        columns: [_lt('Ideas'), _lt('Design'), _lt('Review'), _lt('Send'), _lt('Done')],
        description: _lt("Collect ideas, design creative content and publish it once reviewed."),
    }, {
        name: _lt('Event-driven Flow'),
        columns: [_lt('Later'), _lt('This Month'), _lt('This Week'), _lt('Running'), _lt('Sent')],
        description: _lt("Track incoming events (e.g. : Christmas, Black Friday, ...) and publish timely content."),
    }, {
        name: _lt('Soft-Launch Flow'),
        columns: [_lt('Pre-Launch'), _lt('Soft-Launch'), _lt('Deploy'), _lt('Report'), _lt('Done')],
        description: _lt("Prepare your Campaign, test it with part of your audience and deploy it fully afterwards."),
    }, {
        name: _lt('Audience-driven Flow'),
        columns: [_lt('Gather Data'), _lt('List-Building'), _lt('Copywriting'), _lt('Sent')],
        description: _lt("Gather data, build a recipient list and write content based on your Marketing target."),
    }, {
        name: _lt('Approval-based Flow'),
        columns: [_lt('To be Approved'), _lt('Approved'), _lt('Deployed')],
        description: _lt("Prepare Campaigns and get them approved before making them go live."),
    }],
};

kanbanExamplesRegistry.add('utm_campaign', exampleData);
registry.category("kanban_examples").add("utm_campaign", exampleData);
});
