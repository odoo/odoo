import { Component, proxy, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { ImportErrorResolution } from "../import_error_resolution/import_error_resolution";

export class ImportDataColumnError extends Component {
    static template = "ImportDataColumnError";
    static components = { ImportErrorResolution };

    props = useProps({
        errors: t.array(),
        fieldInfo: t.object(),
        resultNames: t.array(),
        onErrorResolved: t.function(),
    });

    setup() {
        this.state = proxy({ isExpanded: false });
    }

    isErrorVisible(index) {
        return this.state.isExpanded || index < 3;
    }

    getMessageClass(error) {
        return error.reportedBefore && !error.resolution ? "text-danger" : "";
    }

    getErrorText(error) {
        const rowsText = this.getErrorRowsText(error);
        return rowsText ? `${error.message} ${rowsText}` : error.message;
    }

    getErrorRowsText(error) {
        if (!error.rows) {
            return "";
        }
        if (error.rows.from !== error.rows.to) {
            return _t("at rows %(from)s to %(to)s", {
                from: error.rows.from + 1,
                to: error.rows.to + 1,
            });
        }
        const name = this.props.resultNames[error.rows.from];
        return name
            ? _t("at row %(row)s (%(name)s)", { row: error.rows.from + 1, name })
            : _t("at row %(row)s", { row: error.rows.from + 1 });
    }
}
