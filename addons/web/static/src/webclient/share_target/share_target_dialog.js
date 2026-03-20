import { Component, onWillDestroy, onWillStart, useState, useSubEnv } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { generatePdfThumbnail } from "@web/core/utils/pdfjs";
import { ShareTargetItem } from "@web/webclient/share_target/share_target_item";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

export class ShareTargetDialog extends Component {
    static template = "web.ShareTargetDialog";
    static components = { Dialog, ShareTargetItem };
    static props = {
        close: { type: Function },
        files: { type: Array, element: File },
    };

    setup() {
        super.setup();
        this.menu = useService("menu");
        this.shareTargetItems = registry
            .category("share_target_items")
            .getAll()
            .sort(({ sequence: sequenceA }, { sequence: sequenceB }) => sequenceA - sequenceB);
        this.state = useState({
            selectedShareTargetItemIndex: 0,
            previewFileUrl: URL.createObjectURL(this.props.files[0]),
            previewFileIndex: 0,
        });
        this.hooks = {
            save: async () => {},
        };
        useSubEnv({
            setHook: (hooks) => {
                this.hooks = hooks;
            },
        });
        onWillStart(async () => {
            // generate preview if we use pdf
            if (this.previewFile.type.includes("pdf")) {
                await this._generatePdfPreview();
            }
        });
        onWillDestroy(() => URL.revokeObjectURL(this.state.previewFileUrl));
    }

    async _generatePdfPreview() {
        const { thumbnail } = await generatePdfThumbnail(this.state.previewFileUrl, {
            height: 768,
            width: 768,
        });
        URL.revokeObjectURL(this.state.previewFileUrl);
        this.state.previewFileUrl = `data:image/jpeg;base64,${thumbnail}`;
    }

    get previewFile() {
        return this.props.files[this.state.previewFileIndex];
    }

    isSelectedShareTarget(name) {
        return this.shareTargetItems[this.state.selectedShareTargetItemIndex].name === name;
    }

    onSelectedApp(name) {
        const index = this.shareTargetItems.findIndex(
            (shareTargetItem) => shareTargetItem.name === name
        );
        if (index > -1) {
            this.state.selectedShareTargetItemIndex = index;
        }
    }

    async save(ev) {
        ev.target.disabled = true;
        await this.hooks.save();
        this.props.close();
    }
}
