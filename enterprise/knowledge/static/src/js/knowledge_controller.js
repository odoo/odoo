/** @odoo-module **/

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { FormController } from '@web/views/form/form_controller';
import { KnowledgeSidebar } from '@knowledge/components/sidebar/sidebar';
import { useBus, useService } from "@web/core/utils/hooks";
import { Deferred } from "@web/core/utils/concurrency";

import {
    onMounted,
    onWillStart,
    useChildSubEnv,
    useEffect,
    useExternalListener,
    useRef,
} from "@odoo/owl";

export class KnowledgeArticleFormController extends FormController {
    static template = "knowledge.ArticleFormView";
    // Open articles in edit mode by default
    static defaultProps = {
        ...FormController.defaultProps,
        mode: "edit",
    };
    static components = {
        ...FormController.components,
        KnowledgeSidebar,
    };

    setup() {
        super.setup();
        this.root = useRef('root');
        this.orm = useService('orm');
        this.actionService = useService('action');
        this.dialogService = useService("dialog");

        /*
            Because of the way OWL is designed we are never sure when OWL finishes mounting this component.
            Thus, we added this deferred promise in order for us to know when it is done.
            It is necessary to have this because the comments handler needs to notify the topbar when
            it has detected comments so that it can show the comments panel's button.
        */
        this.topbarMountedPromise = new Deferred();

        useChildSubEnv({
            createArticle: this.createArticle.bind(this),
            ensureArticleName: this.ensureArticleName.bind(this),
            openArticle: this.openArticle.bind(this),
            renameArticle: this.renameArticle.bind(this),
            toggleAsideMobile: this.toggleAsideMobile.bind(this),
            topbarMountedPromise: this.topbarMountedPromise,
            save: this.save.bind(this),
            discard: this.discard.bind(this),
        });

        useBus(this.env.bus, 'KNOWLEDGE:OPEN_ARTICLE', (event) => {
            this.openArticle(event.detail.id);
        });

        // Unregister the current candidate recordInfo for Knowledge macros in
        // case of breadcrumbs mismatch.
        onWillStart(() => {
            if (
                !this.env.inDialog &&
                this.env.config.breadcrumbs &&
                this.env.config.breadcrumbs.length
            ) {
                // Unregister the current candidate recordInfo in case of
                // breadcrumbs mismatch.
                this.knowledgeCommandsService.unregisterCommandsRecordInfo(this.env.config.breadcrumbs);
            }
        });
        onMounted(() => {
            this.topbarMountedPromise.resolve();
        });

        useExternalListener(document.documentElement, 'mouseleave', async () => {
            if (await this.model.root.isDirty()) {
                await this.model.root.save();
            }
        });

        useEffect(
            () => {
                const scrollView = this.root.el?.querySelector(".o_scroll_view_lg");
                if (scrollView) {
                    scrollView.scrollTop = 0;
                }
                const mobileScrollView = this.root.el?.querySelector(".o_knowledge_main_view");
                if (mobileScrollView) {
                    mobileScrollView.scrollTop = 0;
                }
            },
            () => [this.model.root.resId]
        );
    }

    /**
     * Ensure that the title is set @see beforeUnload
     * Dirty check is sometimes necessary in cases where the user leaves
     * the article from inside an article (i.e. embedded views/links) very
     * shortly after a mutation (i.e. in tours). At that point, the
     * html_field may not have notified the model from the change.
     * @override
     */
    async beforeLeave() {
        if (this.model.root.resId) {
            await this.ensureArticleName();
        }
        await this.model.root.isDirty();
        return super.beforeLeave();
    }

    /**
     * Check that the title is set or not before closing the tab and
     * save the whole article, if the current article exists (it does
     * not exist if there are no articles to show, in which case the no
     * content helper is displayed).
     * @override
     */
    async beforeUnload(ev) {
        if (this.model.root.resId) {
            await this.ensureArticleName();
            if (await this.model.root.isDirty()) {
                await super.beforeUnload(ev); // triggers an urgent save
            }
        }
    }

    /**
     * If the article has no name set, tries to rename it.
     */
    ensureArticleName() {
        const recordData = this.model.root.data;
        if (
            !recordData.name &&
            !(recordData.is_locked || !recordData.user_can_write || !recordData.active)
        ) {
            return this.renameArticle();
        }
    }

    get resId() {
        return this.model.root.resId;
    }

    /**
     * Create a new article and open it.
     * @param {String} category - Category of the new article
     * @param {integer} targetParentId - Id of the parent of the new article (optional)
     */
    async createArticle(category, targetParentId) {
        const articleId = await this.orm.call(
            "knowledge.article",
            "article_create",
            [],
            {
                is_private: category === 'private',
                parent_id: targetParentId ? targetParentId : false
            }
        );
        this.openArticle(articleId);
    }

    getHtmlTitle() {
        const titleEl = this.root.el.querySelector(".note-editable.odoo-editor-editable h1");
        if (titleEl) {
            const title = titleEl.textContent.trim();
            if (title) {
                return title;
            }
        }
    }

    displayName() {
        return this.model.root.data.name || _t("New");
    }

    /**
     * Callback executed before the record save (if the record is valid).
     * When an article has no name set, use the title (first h1 in the
     * body) to try to save the article with a name.
     * @overwrite
     */
    async onWillSaveRecord(record, changes) {
        if (!record.data.name) {
            const title = this.getHtmlTitle();
            if (title) {
                changes.name = title;
            }
         }
    }

    /**
     * @param {integer} - resId: id of the article to open
     */
    async openArticle(resId) {
        if (!resId || resId === this.resId) {
            return;
        }

        // blur to remove focus on the active element
        document.activeElement.blur();

        // load the new record
        try {
            if (this.model.root.isNew) {
                await this.model.load({ resId });
            } else {
                await this.ensureArticleName();
                if (await this.model.root.isDirty()) {
                    await this.model.root.save({
                        onError: this.onSaveError.bind(this),
                        nextId: resId,
                    });
                } else {
                    await this.model.load({ resId });
                }
            }
        } catch {
            this.dialogService.add(AlertDialog, {
                title: _t("Access Denied"),
                body: _t(
                    "The article you are trying to open has either been removed or is inaccessible.",
                ),
                confirmLabel: _t("Close"),
            });
        }
        this.toggleAsideMobile(false);
    }

    /*
     * Rename the article using the given name, or using the article title if
     * no name is given (first h1 in the body). If no title is found, the
     * article is kept untitled.
     * @param {string} name - new name of the article
     */
    renameArticle(name) {
        if (!name) {
            const title = this.getHtmlTitle();
            if (!title) {
                return;
            }
            name = title;
        }
        return this.model.root.update({ name });
    }

    /**
     * Toggle the aside menu on mobile devices (< 576px).
     * @param {boolean} force
     */
    toggleAsideMobile(force) {
        const container = this.root.el.querySelector('.o_knowledge_form_view');
        container.classList.toggle('o_toggle_aside', force);
    }
}
