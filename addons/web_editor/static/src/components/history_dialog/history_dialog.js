/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { Notebook } from '@web/core/notebook/notebook';
import { formatDateTime } from '@web/core/l10n/dates';
import { useService } from '@web/core/utils/hooks';
import { memoize } from '@web/core/utils/functions';
import { Component, onMounted, useState, markup } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { user } from "@web/core/user";

const { DateTime } = luxon;

class HistoryDialog extends Component {
    static template = 'web_editor.HistoryDialog';
    static components = { Dialog, Notebook };
    static props = {
        recordId: Number,
        recordModel: String,
        close: Function,
        restoreRequested: Function,
        historyMetadata: Array,
        versionedFieldName: String,
        title: { String, optional: true },
        noContentHelper: { String, optional: true }, //Markup
    };

    static defaultProps = {
        title: _t("History"),
        noContentHelper: markup(""),
    };

    state = useState({
        revisionsData: [],
        revisionContent: null,
        revisionComparison: null,
        revisionId: null
    });

    setup() {
        this.size = 'xl';
        this.title = this.props.title;
        this.orm = useService('orm');
        this.notebookTabs = [_t("Content"), _t("Comparison")];

        onMounted(() => this.init());
    }

    async init() {
        this.state.revisionsData = this.props.historyMetadata;
        await this.updateCurrentRevision(this.props.historyMetadata[0]['revision_id']);
    }

    async updateCurrentRevision(revisionId) {
        if (this.state.revisionId === revisionId) {
            return;
        }
        this.state.revisionId = revisionId;
        this.state.revisionContent = await this.getRevisionContent(revisionId);
        this.state.revisionComparison = await this.getRevisionComparison(
            revisionId
        );
    }

    getRevisionComparison = memoize(
        async function getRevisionComparison(revisionId) {
            const comparison = await this.orm.call(
                this.props.recordModel,
                'html_field_history_get_comparison_at_revision',
                [this.props.recordId, this.props.versionedFieldName, revisionId]
            );
            return markup(comparison);
        }.bind(this)
    );

    getRevisionContent = memoize(
        async function getRevisionContent(revisionId) {
            const content = await this.orm.call(
                this.props.recordModel,
                'html_field_history_get_content_at_revision',
                [this.props.recordId, this.props.versionedFieldName, revisionId]
            );
            return markup(content);
        }.bind(this)
    );

    async _onRestoreRevisionClick() {
        const restoredContent = await this.getRevisionContent(
            this.state.revisionId
        );
        this.props.restoreRequested(restoredContent, this.props.close);
    }

    /**
     * Getters
     **/
    getRevisionDate(revision) {
        return formatDateTime(DateTime.fromISO(revision['create_date'], { zone: 'utc' }).setZone(user.tz));
    }
}

export default HistoryDialog;
