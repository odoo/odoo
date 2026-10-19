import { Component, t, useProps } from "@odoo/owl";

import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

/**
 * Asks confirmation before deleting attachments standing for several copies,
 * offering to drop the whole groups or only the redundant copies.
 */
export class AttachmentDeleteDialog extends Component {
    static components = { Dialog };
    static template = "mail.AttachmentDeleteDialog";

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.props = useProps({
            close: t.function(),
            groups: t.array(
                t.object({
                    attachment: t.instanceOf(this.store["ir.attachment"]),
                    duplicates: t.array(t.instanceOf(this.store["ir.attachment"])),
                })
            ),
            onDelete: t.function([t.array(t.instanceOf(this.store["ir.attachment"]))]),
        });
    }

    get title() {
        return _t("Delete Attachments");
    }

    get body() {
        const [group] = this.props.groups;
        if (this.props.groups.length === 1) {
            return _t(
                'Are you sure you want to delete the %(count)s copies of "%(name)s"?\nThis action cannot be undone.',
                { count: group.duplicates.length, name: group.attachment.name }
            );
        }
        return _t(
            "Are you sure you want to delete the %(count)s selected files and their copies?\nThis action cannot be undone.",
            { count: this.props.groups.length }
        );
    }

    get deleteAllLabel() {
        return this.props.groups.length === 1
            ? _t("Delete Attachment & Duplicates")
            : _t("Delete All");
    }

    /** Copies that a group could be reduced to a single attachment by deleting. */
    get redundantAttachments() {
        return this.props.groups.flatMap(({ attachment, duplicates }) =>
            duplicates.filter((duplicate) => duplicate.notEq(attachment))
        );
    }

    onClickDeleteAll() {
        this.props.onDelete(this.props.groups.flatMap((group) => group.duplicates));
        this.props.close();
    }

    onClickDeleteDuplicates() {
        this.props.onDelete(this.redundantAttachments);
        this.props.close();
    }
}
