import { Component, proxy, t, useProps } from "@odoo/owl";
import { ImportErrorResolution } from "../import_error_resolution/import_error_resolution";
import { formatErrorRows } from "../import_model";

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
        const rowsText = formatErrorRows(error, this.props.resultNames);
        return rowsText ? `${error.message} ${rowsText}` : error.message;
    }
}
