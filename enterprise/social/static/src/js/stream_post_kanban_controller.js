/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { AddSocialStreamDialog } from './add_stream_modal';
import { NewContentRefreshBanner } from './stream_post_kanban_refresh_banner';
import { StreamPostDashboard } from './stream_post_kanban_dashboard';
import { useModelWithSampleData } from "@web/model/model";

import { KanbanController } from '@web/views/kanban/kanban_controller';
import { user } from "@web/core/user";
import { useService } from '@web/core/utils/hooks';
import { onWillStart, useEffect, useSubEnv, useState } from "@odoo/owl";

export class StreamPostKanbanController extends KanbanController {
    static template = "social.SocialKanbanView";
    static components = {
        ...KanbanController.components,
        NewContentRefreshBanner,
        StreamPostDashboard,
    };

    setup() {
        super.setup();
        this.model = useModelWithSampleData(this.props.Model, this.modelParams);
        this.company = useService('company');
        this.dialog = useService('dialog');
        this.orm = useService('orm');
        this.notification = useService('notification');
        this.state = useState({
            refreshRequired: false,
            disableSyncButton: false,
        });
        useSubEnv({
            refreshStats: this._onRefreshStats.bind(this)
        });

        useEffect((addStreamLink) => {
            if (addStreamLink) {
                addStreamLink.addEventListener('click', this._onNewStream.bind(this));
            }
        }, () => [document.querySelector('.o_social_js_add_stream')]);

        onWillStart(async () => {
            this.isSocialManager = await user.hasGroup("social.group_social_manager");
            this.hasAccounts = await this.orm.searchCount('social.account', []) > 0;
            this.accounts = await this.model._loadAccountsStats();
        });
        onWillStart(() => this._onRefreshStats());
    }

    async _onRefreshStats() {
        this.state.disableSyncButton = true;
        Promise.all([
            this.model._refreshStreams().then((result) => {
                this.state.refreshRequired = result;
            }),
            this.model._refreshAccountsStats().then((result) => {
                this.accounts = result;
            }),
        ]).then(() => this.state.disableSyncButton = false);
    }

    _refreshView() {
        this.state.refreshRequired = false;
        this.model.load();
    }

    _onNewPost() {
        this.actionService.doAction({
            name: _t('New Post'),
            type: 'ir.actions.act_window',
            res_model: 'social.post',
            views: [[false, "form"]],
        });
    }

    _onNewStream() {
        if (this.accounts.length > 0 || this.isSocialManager) {
            this._addNewStream();
        } else {
            this.notification.add(
                _t("No social accounts configured, please contact your administrator."),
                { type: 'danger' }
            );
        }
    }

    _addNewStream() {
        this._fetchSocialMedia().then((socialMedia) =>
            this.dialog.add(AddSocialStreamDialog, {
                title: _t('Add a Stream'),
                isSocialManager: this.isSocialManager,
                socialMedia: socialMedia,
                socialAccounts: this.accounts,
                companies: this._getCompanies(),
                onSaved: this._onStreamAdded.bind(this),
            })
        )
    }

    async _onStreamAdded(stream) {
        const streams = await this.orm.searchRead(
            'social.stream',
            [
                ['id', '=', stream.data.id],
                ['stream_post_ids', '=', false]
            ],
            ['name']);
        if (streams.length) {
            this.notification.add(
                _t("It will appear in the Feed once it has posts to display."),
                { title: _t("Stream Added (%s)", streams[0].name), type: "success" }
            );
        } else {
            await this.model.load();
            this.model.notify();
        }
    }

    /**
     * Fetches media on which you can add remote accounts and streams.
     * We check the fact that they handle streams.
     *
     * @private
     */
    async _fetchSocialMedia() {
        if (this.socialMedia) {
            return this.socialMedia;
        } else {
            this.socialMedia = await this.orm.searchRead(
                'social.media',
                [['has_streams', '=', 'True']],
                ['id', 'name'],
            );
            return this.socialMedia;
        }
    }

    /**
     * Return the list of allowed companies for the current users.
     * The first element of the array is the current selected company.
     *
     * @private
     * @param {Array} [{id: company_id, name: company_name}, ...]
     */
    _getCompanies() {
        const companies = this.company.allowedCompanies;
        return this.company.activeCompanyIds.map(companyId => companies[companyId]);
    }

}
