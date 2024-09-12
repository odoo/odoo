/** @odoo-module **/

import { Dialog } from '@web/core/dialog/dialog';
import { Notebook } from '@web/core/notebook/notebook';
import { formatDateTime } from '@web/core/l10n/dates';
import { useService } from '@web/core/utils/hooks';
import { memoize } from '@web/core/utils/functions';
import { Component, onMounted, useRef, useState, markup } from '@odoo/owl';
import { _t } from '@web/core/l10n/translation';
import { user } from "@web/core/user";
import {localization} from "@web/core/l10n/localization";

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
        revisionContentMetadata: "",
        revisionComparisonMetadata: "",
        revisionId: null,
        currentRevision: null
    });

    setup() {
        this.size = 'xl';
        this.title = this.props.title;
        this.orm = useService('orm');
        this.historyContainer = useRef("history-container");
        this.notebookTabs = [_t("Content"), _t("Comparison")];
        onMounted(() => this.init());
    }

    async init() {
        let previousLoopDate;
        for(let metadata of this.props.historyMetadata) {
            const date = DateTime.fromISO(metadata.create_date, { zone: 'utc' }).startOf('day').ts;
            if(!previousLoopDate || date !== previousLoopDate) {
                this.state.revisionsData.push({...metadata,...{detailedData:[], allRevisionIds:[]}});
            }
            const lasRevDataIndex = this.state.revisionsData.length - 1;
            this.state.revisionsData[lasRevDataIndex].detailedData.push(metadata);
            this.state.revisionsData[lasRevDataIndex].allRevisionIds.push(metadata.revision_id);
            previousLoopDate = date;
        }
        await this.updateCurrentRevision(this.props.historyMetadata[0]['revision_id']);
    }

    async updateCurrentRevision(revisionId) {
        const pane = this.historyContainer?.el.querySelector(".o_notebook_content");
        if (pane) {
            pane.scrollTop = 0;
        }
        if (this.state.revisionId === revisionId) {
            return;
        }
        this.state.revisionId = revisionId;
        this.state.currentRevision = this.props.historyMetadata.find(entry => entry.revision_id === this.state.revisionId);
        this.state.revisionContent = await this.getRevisionContent(revisionId);
        this.state.revisionComparison = await this.getRevisionComparison(
            revisionId
        );
        this.state.revisionContentMetadata = _t(
            "Showing the document from the %s.",
            this.getRevisionDateTime(this.state.currentRevision)
        );
        this.state.revisionComparisonMetadata = _t(
            "Showing all updates since the %s version in comparison to your version.",
            this.getRevisionDateTime(this.state.currentRevision)
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
    getRevisionDate(revision, format=localization.dateFormat) {
        if (!revision) {
            return "";
        }
        return formatDateTime(
            DateTime.fromISO(
                revision['create_date'],
                { zone: 'utc'}
            ).setZone(user.tz),
            {format: format}
        );
    }
    getRevisionHour(revision) {
        return this.getRevisionDate(revision, localization.timeFormat)
    }
    getRevisionDateTime(revision) {
        return this.getRevisionDate(revision, localization.dateTimeFormat)
    }
}

export default HistoryDialog;
