import { Component, signal, t, useOnChange, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useModel } from "@web/model/model";
import { useSetupAction } from "@web/search/action_hook";
import { Layout } from "@web/search/layout";
import { usePager } from "@web/search/pager_hook";
import { standardViewProps } from "@web/views/standard_view_props";

/**
 * @typedef {import("./new_relational_model").NewRelationalModel} NewRelationalModel
 */

/**
 * Save and discard buttons, shown while the record has unsaved changes.
 *
 * A component of its own so that it is the only one to subscribe to the dirty
 * state, which changes on every edit.
 */
class FormSignalStatusIndicator extends Component {
    static template = "web.FormSignalView.StatusIndicator";

    props = useProps({
        model: t.object(),
        save: t.function(),
        discard: t.function(),
    });
}

/**
 * Creates the model, and wires it to the action: control panel buttons,
 * pager, breadcrumbs and url. Everything about the record goes through the
 * model, everything about displaying it is left to the renderer.
 */
export class FormSignalController extends Component {
    static template = "web.FormSignalView";
    static components = { Layout, FormSignalStatusIndicator };

    props = useProps({
        ...standardViewProps,
        Model: t.function(),
        Renderer: t.function(),
        archInfo: t.object(),
    });

    rootRef = signal.ref();

    setup() {
        const { archInfo, resModel, resId, resIds, fields, context } = this.props;
        this.canCreate = archInfo.activeActions.create;
        this.canEdit = archInfo.activeActions.edit;

        /** @type {NewRelationalModel} */
        this.model = useModel(this.props.Model, {
            resModel,
            fields,
            fieldNames: archInfo.fieldNames,
            context,
            resId: resId || false,
            resIds: resIds || (resId ? [resId] : []),
        });

        // Keep the breadcrumbs and the url in sync with the displayed record.
        // Only the first function is tracked: the callback must not be, as
        // `setDisplayName` reads and writes the (reactive) breadcrumbs, which
        // would re-run it forever.
        useOnChange(
            () => [this.model.root(), this.model.resId(), this.model.root()?.display_name()],
            (record, resId, displayName) => {
                if (record) {
                    this.env.config.setDisplayName(resId ? displayName || "" : _t("New"));
                    this.props.updateActionState?.({ resId });
                }
            }
        );

        useSetupAction({
            rootRef: this.rootRef,
            beforeLeave: () => this.saveIfDirty(),
            getLocalState: () => ({ resId: this.model.resId() }),
        });

        usePager(() => {
            if (this.model.isNew()) {
                return; // no pager on a new record
            }
            const { resIds } = this.model;
            return {
                offset: resIds.indexOf(this.model.resId()),
                limit: 1,
                total: resIds.length,
                onUpdate: async ({ offset }) => {
                    await this.saveIfDirty();
                    await this.model.load({ resId: resIds[offset] });
                },
            };
        });
    }

    async saveIfDirty() {
        if (this.model.isDirty()) {
            await this.model.save();
        }
    }

    async create() {
        await this.saveIfDirty();
        await this.model.load({ resId: false });
    }

    async save() {
        await this.model.save();
    }

    discard() {
        const isNew = this.model.isNew();
        this.model.discard();
        if (isNew) {
            // a discarded new record is gone: back to what was displayed before
            this.env.config.historyBack();
        }
    }
}
