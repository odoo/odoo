/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { renderToMarkup } from '@web/core/utils/render';

const { markup } = owl;
const greenBullet = markup(`<span class="o_status d-inline-block o_status_green"></span>`);
const orangeBullet = markup(`<span class="o_status d-inline-block text-warning"></span>`);
const star = markup(`<a style="color: gold;" class="fa fa-star"></a>`);
const clock = markup(`<a class="fa fa-clock-o"></a>`);

const exampleData = {
    ghostColumns: [_lt('New'), _lt('Assigned'), _lt('In Progress'), _lt('Done')],
    applyExamplesText: _lt("Use This For My Project"),
    allowedGroupBys: ['stage_id'],
    foldField: "fold",
    examples:[{
        name: _lt('Software Development'),
        columns: [_lt('Backlog'), _lt('Specifications'), _lt('Development'), _lt('Tests')],
        foldedColumns: [_lt('Delivered')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star],
    }, {
        name: _lt('Agile Scrum'),
        columns: [_lt('Backlog'), _lt('Sprint Backlog'), _lt('Sprint in Progress')],
        foldedColumns: [_lt('Sprint Complete'), _lt('Old Completed Sprint')],
        get description() {
            return renderToMarkup("project.example.agilescrum");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _lt('Digital Marketing'),
        columns: [_lt('Ideas'), _lt('Researching'), _lt('Writing'), _lt('Editing')],
        foldedColumns: [_lt('Done')],
        get description() {
            return renderToMarkup("project.example.digitalmarketing");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _lt('Customer Feedback'),
        columns: [_lt('New'), _lt('In development')],
        foldedColumns: [_lt('Done'), _lt('Refused')],
        get description() {
            return renderToMarkup("project.example.customerfeedback");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _lt('Consulting'),
        columns: [_lt('New Projects'), _lt('Resources Allocation'), _lt('In Progress')],
        foldedColumns: [_lt('Done')],
        get description() {
            return renderToMarkup("project.example.consulting");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _lt('Research Project'),
        columns: [_lt('Brainstorm'), _lt('Research'), _lt('Draft')],
        foldedColumns: [_lt('Final Document')],
        get description() {
            return renderToMarkup("project.example.researchproject");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _lt('Website Redesign'),
        columns: [_lt('Page Ideas'), _lt('Copywriting'), _lt('Design')],
        foldedColumns: [_lt('Live')],
        get description() {
            return renderToMarkup("project.example.researchproject");
        },
    }, {
        name: _lt('T-shirt Printing'),
        columns: [_lt('New Orders'), _lt('Logo Design'), _lt('To Print')],
        foldedColumns: [_lt('Done')],
        get description() {
            return renderToMarkup("project.example.tshirtprinting");
        },
        bullets: [star],
    }, {
        name: _lt('Design'),
        columns: [_lt('New Request'), _lt('Design'), _lt('Client Review')],
        foldedColumns: [_lt('Handoff')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }, {
        name: _lt('Publishing'),
        columns: [_lt('Ideas'), _lt('Writing'), _lt('Editing')],
        foldedColumns: [_lt('Published')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }, {
        name: _lt('Manufacturing'),
        columns: [_lt('New Orders'), _lt('Material Sourcing'), _lt('Manufacturing'), _lt('Assembling')],
        foldedColumns: [_lt('Delivered')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }, {
        name: _lt('Podcast and Video Production'),
        columns: [_lt('Research'), _lt('Script'), _lt('Recording'), _lt('Mixing')],
        foldedColumns: [_lt('Published')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }],
};

registry.category("kanban_examples").add('project', exampleData);
