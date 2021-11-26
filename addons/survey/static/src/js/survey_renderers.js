/** @odoo-module */

import Dialog from 'web.Dialog';
import KanbanRenderer from 'web.KanbanRenderer';
import ListRenderer from 'web.ListRenderer';
import { qweb as QWeb, _t } from 'web.core';

const SurveySampleModalMixin = {
    /**
     * Opens a dialog allowing the user to load a sample survey
     * We currently have 3 different samples to load (and one "tile" to click on
     * for each in the modal).
     * - Sample Feedback Form
     * - Sample Certification
     * - Sample Live Presentation
     */
    _onOpenSurveySampleModalClick: function () {
        const $content = $(QWeb.render('survey.survey_sample_modal_body'));
        $content.find('.o_survey_sample_tile').each((_index, tile) => {
            const $tile = $(tile);
            $tile.on('click', async () => {
                const surveySampleAction = await this._rpc({
                    model: 'survey.survey',
                    method: $tile.data('action'),
                });
                this.do_action(surveySampleAction);
            });
        });
        const dialog = new Dialog(this, {
            title: _t('Load a Survey'),
            $content: $content,
            renderFooter: false,
        });
        dialog.open();
    },
}

const SurveyKanbanRenderer = KanbanRenderer.extend(SurveySampleModalMixin, {
    xmlDependencies: (KanbanRenderer.prototype.xmlDependencies || []).concat([
        'survey/static/src/xml/survey_sample_modal.xml',
    ]),
    events: _.extend({}, KanbanRenderer.prototype.events, {
        'click .o_survey_open_sample_modal': '_onOpenSurveySampleModalClick',
    }),
});

const SurveyListRenderer = ListRenderer.extend(SurveySampleModalMixin, {
    xmlDependencies: (ListRenderer.prototype.xmlDependencies || []).concat([
        'survey/static/src/xml/survey_sample_modal.xml',
    ]),
    events: _.extend({}, ListRenderer.prototype.events, {
        'click .o_survey_open_sample_modal': '_onOpenSurveySampleModalClick',
    }),
});

export {
    SurveyKanbanRenderer,
    SurveyListRenderer,
};
