import { Component, useState } from  '@odoo/owl';
import { Dialog } from '@web/core/dialog/dialog';
import { _t } from '@web/core/l10n/translation';
import { useService } from '@web/core/utils/hooks';

import { FilesList } from '@sale_pdf_quote_builder/js/files_list/files_list';

export class UpdateIncludedPdfDialog extends Component {
    static components = { Dialog, FilesList };
    static template = 'salePdfQuoteBuilder.updateIncludedPdfDialog';
    static props = {
        headers: Object,
        lines: Array,
        footers: Object,
        savePdfs: Function,
        close: Function, // This is the close from the env of the Dialog Component
    };

    setup() {
        this.title = _t("Customize your Quote");
        this.state = useState({
            ...this.props
        })
        this.orm = useService('orm');

    }

    /**
     * Confirm the current setup.
     *
     * @return {undefined}
     */
    async onConfirm() {
        let selectedLinesPdf = [];
        for (const line of this.props.lines) {
            selectedLinesPdf.push({
                'id': line.id,
                'selectedPdfs': line.files.filter(
                    files => files.is_selected
                ).map(files => files.id),
            });
        }
        let selectedPdfs = {
            'header': this.props.headers.files.filter(
                files => files.is_selected
            ).map(files => files.id),
            'lines': selectedLinesPdf,
            'footer': this.props.footers.files.filter(
                files => files.is_selected
            ).map(files => files.id),
        };
        await this.props.savePdfs(selectedPdfs);
        this.props.close();
    }
}
