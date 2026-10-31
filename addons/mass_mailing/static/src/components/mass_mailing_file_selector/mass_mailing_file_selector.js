import { FileSelector } from "@html_editor/main/media/media_dialog/file_selector";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { patch } from "@web/core/utils/patch";

patch(FileSelector.prototype, {
    async uploadUrl(url) {
        if (this.props.resModel != 'mailing.mailing') {
            return super.uploadUrl(url);
        }
        try {
            const attachment = await rpc("/mailing/attachment/add_url_data", {
                url:  new URL(url, window.location.href).href,
                res_model: this.props.resModel,
                res_id: this.props.resId,
            });
            await this.onUploaded(attachment);
        } catch (error) {
            this.notificationService.add(
                error.data?.message || _t("An error occurred while fetching the entered URL."),
                { type: "danger", sticky: true }
            );
        }
    }
})
