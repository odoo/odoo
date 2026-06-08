import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { renderToMarkup } from '@web/core/utils/render';
import { markup } from "@odoo/owl";

const greenBullet = markup`<span class="o_status d-inline-block o_status_green"></span>`;
const orangeBullet = markup`<span class="o_status d-inline-block text-warning"></span>`;
const star = markup`<a style="color: gold;" class="fa fa-star"></a>`;
const clock = markup`<a class="fa fa-clock-o"></a>`;

const exampleData = {
    applyExamplesText: _t("Use This For My Project"),
    allowedGroupBys: ['stage_id'],
    foldField: "fold",
    examples:[{
        name: _t('Software Development'),
        columns: [_t('Backlog'), _t('Specifications'), _t('Development'), _t('Tests')],
        foldedColumns: [_t('Delivered')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star],
    }, {
        name: _t('Agile Scrum'),
        columns: [_t('Backlog'), _t('Sprint Backlog'), _t('Sprint in Progress')],
        foldedColumns: [_t('Sprint Complete'), _t('Old Completed Sprint')],
        get description() {
            return renderToMarkup("project.example.agilescrum");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _t('Digital Marketing'),
        columns: [_t('Ideas'), _t('Researching'), _t('Writing'), _t('Editing')],
        foldedColumns: [_t('Done')],
        get description() {
            return renderToMarkup("project.example.digitalmarketing");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _t('Customer Feedback'),
        columns: [_t('New'), _t('In development')],
        foldedColumns: [_t('Done'), _t('Refused')],
        get description() {
            return renderToMarkup("project.example.customerfeedback");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _t('Consulting'),
        columns: [_t('New Projects'), _t('Resources Allocation'), _t('In Progress')],
        foldedColumns: [_t('Done')],
        get description() {
            return renderToMarkup("project.example.consulting");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _t('Research Project'),
        columns: [_t('Brainstorm'), _t('Research'), _t('Draft')],
        foldedColumns: [_t('Final Document')],
        get description() {
            return renderToMarkup("project.example.researchproject");
        },
        bullets: [greenBullet, orangeBullet],
    }, {
        name: _t('Website Redesign'),
        columns: [_t('Page Ideas'), _t('Copywriting'), _t('Design')],
        foldedColumns: [_t('Live')],
        get description() {
            return renderToMarkup("project.example.researchproject");
        },
    }, {
        name: _t('T-shirt Printing'),
        columns: [_t('New Orders'), _t('Logo Design'), _t('To Print')],
        foldedColumns: [_t('Done')],
        get description() {
            return renderToMarkup("project.example.tshirtprinting");
        },
        bullets: [star],
    }, {
        name: _t('Design'),
        columns: [_t('New Request'), _t('Design'), _t('Client Review')],
        foldedColumns: [_t('Handoff')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }, {
        name: _t('Publishing'),
        columns: [_t('Ideas'), _t('Writing'), _t('Editing')],
        foldedColumns: [_t('Published')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }, {
        name: _t('Manufacturing'),
        columns: [_t('New Orders'), _t('Material Sourcing'), _t('Manufacturing'), _t('Assembling')],
        foldedColumns: [_t('Delivered')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }, {
        name: _t('Podcast and Video Production'),
        columns: [_t('Research'), _t('Script'), _t('Recording'), _t('Mixing')],
        foldedColumns: [_t('Published')],
        get description() {
            return renderToMarkup("project.example.generic");
        },
        bullets: [greenBullet, orangeBullet, star, clock],
    }],
};

registry.category("kanban_examples").add('project', exampleData);
