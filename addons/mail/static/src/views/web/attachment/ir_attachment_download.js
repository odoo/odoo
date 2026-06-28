import { _t } from "@web/core/l10n/translation";
import { serializeDate } from "@web/core/l10n/dates";
import { download } from "@web/core/network/download";

const { DateTime } = luxon;

const MAX_DOWNLOAD_FILES = 20;

export const IrAttachmentDownload = (component) =>
    class extends component {
        async onDownload() {
            const root = this.model.root;
            const validAttachments = root.selection.filter((att) => att.data.type === "binary");
            const invalidAttachments = root.selection.filter((att) => att.data.type !== "binary");
            const addNotif = this.env.services.notification.add;
            if (validAttachments.length > MAX_DOWNLOAD_FILES) {
                addNotif(_t("You can only download %s files at a time.", MAX_DOWNLOAD_FILES), {
                    type: "danger",
                });
                return;
            }
            if (invalidAttachments.length) {
                addNotif(_t("Only files will be downloaded."), { type: "warning" });
            }
            if (root.isDomainSelected) {
                addNotif(_t("Only the selected files will be downloaded."), { type: "warning" });
            }
            if (!invalidAttachments && !root.isDomainSelected) {
                addNotif(_t("Your download will start soon."), { type: "info" });
            }
            if (validAttachments.length === 1) {
                return download({ data: { id: validAttachments[0].resId }, url: "/web/content" });
            }
            return download({
                data: {
                    file_ids: validAttachments.map((r) => r.resId),
                    zip_name: `attachments-${serializeDate(DateTime.now())}.zip`,
                },
                url: "/mail/attachment/zip",
            });
        }

        getStaticActionMenuItems() {
            return {
                ...super.getStaticActionMenuItems(),
                downloadAttachments: {
                    callback: () => this.onDownload(),
                    description: _t("Download"),
                    icon: "fa fa-download",
                    isAvailable: () =>
                        this.model.root.selection.some((a) => a.data.type === "binary"),
                    sequence: 15,
                },
            };
        }
    };
