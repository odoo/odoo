import { useRef, useState } from "@web/owl2/utils";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { memoize } from "@web/core/utils/functions";
import { Component, onMounted, markup, onWillStart } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { HtmlViewer } from "@html_editor/components/html_viewer/html_viewer";
import { READONLY_MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { browser } from "@web/core/browser/browser";
import { cookie } from "@web/core/browser/cookie";
import { loadBundle } from "@web/core/assets";
import { htmlReplaceAll } from "@web/core/utils/html";
import { scrollTo } from "@web/core/utils/scrolling";

const { DateTime } = luxon;

export class HistoryDialog extends Component {
    static template = "html_editor.HistoryDialog";
    static components = { Dialog, HtmlViewer };
    static props = {
        recordId: Number,
        recordModel: String,
        close: Function,
        restoreRequested: Function,
        historyMetadata: Array,
        versionedFieldName: String,
        title: { String, optional: true },
        noContentHelper: { String, optional: true }, //Markup
        embeddedComponents: { Array, optional: true },
    };

    DEFAULT_AVATAR = "/mail/static/src/img/smiley/avatar.jpg";

    static defaultProps = {
        title: _t("History"),
        noContentHelper: markup(""),
        embeddedComponents: [...READONLY_MAIN_EMBEDDINGS],
    };

    state = useState({
        revisionsData: [],
        currentView: "content", // "content" or "comparison"
        isComparisonSplit: false, // true for side-by-side, false for unified diff
        revisionContent: null,
        revisionComparison: null,
        revisionId: null,
        isLoading: true,
        size: "xl",
        mobileActiveTab: "revisions",
    });

    setup() {
        this.title = this.props.title;
        this.orm = useService("orm");
        this.toggleFullscreen = this.toggleFullscreen.bind(this);
        this.listboxRef = useRef("listbox");

        useHotkey("ArrowUp", () => this.navigateRevisions("PREV"), { allowRepeat: true });
        useHotkey("ArrowDown", () => this.navigateRevisions("NEXT"), { allowRepeat: true });

        onWillStart(async () => {
            // We include the current document version as the first revision,
            // and we shift the rest of the metadata to be more logical for the user.
            let revisionId = -1;
            const revisionData = [];
            for (const metadata of this.props.historyMetadata) {
                revisionData.push({ ...metadata, revision_id: revisionId });
                revisionId = metadata["revision_id"];
            }
            // add the initial revision data based on the record creation date and user
            const record = await this.orm.read(
                this.props.recordModel,
                [this.props.recordId],
                ["create_date", "create_uid"]
            );
            revisionData.push({
                revision_id: revisionId,
                create_date: DateTime.fromFormat(
                    record[0]["create_date"],
                    "yyyy-MM-dd HH:mm:ss"
                ).toISO(),
                create_uid: record[0]["create_uid"][0],
                create_user_name: record[0]["create_uid"][1],
            });

            this.state.revisionsData = revisionData;
        });
        onMounted(() => this.init());
    }

    toggleFullscreen() {
        this.state.size = this.state.size === "xl" ? "fullscreen" : "xl";
    }

    toggleComparison() {
        this.state.currentView = this.state.currentView === "comparison" ? "content" : "comparison";
    }

    setComparisonUnified() {
        this.state.isComparisonSplit = false;
    }

    setComparisonSplit() {
        this.state.isComparisonSplit = true;
    }

    setMobileTab(tab) {
        this.state.mobileActiveTab = tab;
    }

    onRevisionKeydown(revisionId, ev) {
        if (ev.key === 'Enter' || ev.key === ' ') {
            ev.preventDefault();
            this.updateCurrentRevision(revisionId);
        }
    }

    getConfig(value) {
        return {
            value: this.state[value],
            embeddedComponents: this.props.embeddedComponents,
        };
    }

    async init() {
        // Load diff2html only in debug mode, as the side-by-side comparison is only available in debug mode.
        if (this.env.debug) {
            await loadBundle("html_editor.assets_history_diff");
        }
        await this.updateCurrentRevision(this.state.revisionsData[0]["revision_id"]);
    }

    async updateCurrentRevision(revisionId) {
        if (this.state.revisionId === revisionId) {
            return;
        }
        this.state.isLoading = true;
        this.state.revisionId = revisionId;
        this.state.revisionContent = await this.getRevisionContent(revisionId);
        this.state.revisionComparison = await this.getRevisionComparison(revisionId);
        this.state.revisionComparisonSplit = await this.getRevisionComparisonSplit(revisionId);
        this.state.isLoading = false;
        this.state.mobileActiveTab = "content";
    }

    get isMobileActiveTab() {
        return (tab) => this.state.mobileActiveTab === tab;
    }

    get userTZ() {
        return user.tz || "local";
    }

    getRevisionComparison = memoize(
        async function getRevisionComparison(revisionId) {
            if (revisionId === -1) {
                return "";
            }
            const comparison = await this.orm.call(
                this.props.recordModel,
                "html_field_history_get_comparison_at_revision",
                [this.props.recordId, this.props.versionedFieldName, revisionId]
            );
            return this._removeExternalBlockHtml(markup(comparison));
        }.bind(this)
    );

    getRevisionComparisonSplit = memoize(
        async function getRevisionComparisonSplit(revisionId) {
            if (!this.env.debug || revisionId === -1) {
                return "";
            }
            let unifiedDiffString = await this.orm.call(
                this.props.recordModel,
                "html_field_history_get_unified_diff_at_revision",
                [this.props.recordId, this.props.versionedFieldName, revisionId]
            );
            // Remove unnecessary linebreaks
            unifiedDiffString = unifiedDiffString.replace(/^\s*[\r\n]/gm, "");
            const colorScheme = cookie.get("color_scheme") === "dark" ? "dark" : "light";
            // eslint-disable-next-line no-undef
            const diffHtml = Diff2Html.html(unifiedDiffString, {
                drawFileList: false,
                matching: "lines",
                outputFormat: "side-by-side",
                colorScheme: colorScheme,
            });
            return markup(diffHtml);
        }.bind(this)
    );

    getRevisionContent = memoize(
        async function getRevisionContent(revisionId) {
            if (revisionId === -1) {
                const curentContent = await this.orm.read(
                    this.props.recordModel,
                    [this.props.recordId],
                    [this.props.versionedFieldName]
                );
                if (!curentContent || !curentContent.length) {
                    return this.props.noContentHelper;
                }
                return this._removeExternalBlockHtml(
                    markup(curentContent[0][this.props.versionedFieldName])
                );
            }
            const content = await this.orm.call(
                this.props.recordModel,
                "html_field_history_get_content_at_revision",
                [this.props.recordId, this.props.versionedFieldName, revisionId]
            );
            return this._removeExternalBlockHtml(markup(content));
        }.bind(this)
    );

    async _onRestoreRevisionClick() {
        this.env.services.ui.block();
        const restoredContent = await this.getRevisionContent(this.state.revisionId);
        this.props.restoreRequested(restoredContent, this.props.close);
        this.env.services.ui.unblock();
    }

    _removeExternalBlockHtml(baseHtml) {
        const filteringRegex = /<[a-z ]+data-embedded="(?:(?!<).)+<\/[a-z]+>/gim;
        const placeholderHtml = markup`<div class="embedded-history-dialog-placeholder d-flex align-items-center justify-content-center gap-2 p-4 my-2 bg-100 rounded text-muted fw-medium small">${_t(
            "Dynamic element"
        )}</div>`;
        return htmlReplaceAll(baseHtml, filteringRegex, () => placeholderHtml);
    }

    /**
     * Getters
     **/
    getRevisionDate(revision) {
        if (!revision || !revision["create_date"]) {
            return "--";
        }
        const revisionDate = DateTime.fromISO(revision["create_date"], { zone: "utc" }).setZone(this.userTZ);
        const now = DateTime.now().setZone(this.userTZ);
        const diffInMinutes = now.diff(revisionDate, 'minutes').minutes;
        const diffInHours = now.diff(revisionDate, 'hours').hours;

        if (diffInMinutes < 1 && diffInMinutes >= 0) {
            return "Just now";
        }

        if (diffInMinutes < 60 && diffInMinutes >= 1) {
            const minutes = Math.floor(diffInMinutes);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        }

        if (diffInHours < 24 && revisionDate.hasSame(now, 'day')) {
            const hours = Math.floor(diffInHours);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        }

        if (revisionDate.hasSame(now, 'day')) {
            return `Today at ${revisionDate.toFormat('h:mm a')}`;
        }

        if (revisionDate.plus({ days: 1 }).hasSame(now, 'day')) {
            return `Yesterday at ${revisionDate.toFormat('h:mm a')}`;
        }

        if (revisionDate.hasSame(now, 'year')) {
            return revisionDate.toFormat('MMM d \'at\' h:mm a');
        }

        return revisionDate.toFormat('MMM d, yyyy');
    }

    getRevisionFullDate(revision) {
        if (!revision || !revision["create_date"]) {
            return "--";
        }
        const revisionDate = DateTime.fromISO(revision["create_date"], { zone: "utc" }).setZone(this.userTZ);
        return revisionDate.toFormat('MMM d, yyyy \'at\' h:mm:ss a');
    }

    isRevisionSelected(revision) {
        return this.currentRevision?.revision_id === revision.revision_id;
    }

    navigateRevisions(direction) {
        if (!this.state.revisionsData.length) {
            return;
        }

        const currentIndex = this.state.revisionsData.findIndex(
            (rev) => rev.revision_id === this.state.revisionId
        );

        if (currentIndex === -1) {
            this.updateCurrentRevision(this.state.revisionsData[0].revision_id);
            return;
        }

        let nextIndex;
        if (direction === "NEXT") {
            nextIndex = currentIndex < this.state.revisionsData.length - 1 ? currentIndex + 1 : 0;
        } else if (direction === "PREV") {
            nextIndex = currentIndex > 0 ? currentIndex - 1 : this.state.revisionsData.length - 1;
        }

        const nextRevision = this.state.revisionsData[nextIndex];
        this.updateCurrentRevision(nextRevision.revision_id);

        if (this.listboxRef.el) {
            const revisionElement = this.listboxRef.el.querySelector(
                `[data-revision-id="${nextRevision.revision_id}"]`
            );
            if (revisionElement) {
                revisionElement.focus();
                scrollTo(revisionElement, { scrollable: this.listboxRef.el });
            }
        }
    }

    getRevisionClasses(revision) {
        let classesStr = "list-group-item";

        if (
            this.state.revisionId !== -1 &&
            (this.state.revisionId < revision.revision_id || revision.revision_id === -1)
        ) {
            classesStr += " targeted";
        } else if (this.state.revisionId === revision.revision_id) {
            classesStr += " selected";
        }

        return classesStr;
    }
    getRevisionAuthorAvatar(revision) {
        if (!revision || !revision["create_uid"]) {
            return this.DEFAULT_AVATAR;
        }
        return `${browser.location.origin}/web/image?model=res.users&field=avatar_128&id=${revision["create_uid"]}`;
    }

    get currentRevision() {
        const id = this.state?.revisionId || this.state.revisionsData[0]["revision_id"];
        return this.state.revisionsData.find((revision) => revision["revision_id"] === id);
    }
}
