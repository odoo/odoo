/** @odoo-module */

const PAPER_TO_CSS = {
    margin_top: "padding-top",
    margin_left: "padding-left",
    margin_right: "padding-right",
    print_page_width: "width",
    print_page_height: "min-height",
};

export function getCssFromPaperFormat(paperFormat, unit = "mm") {
    return Object.entries(paperFormat)
        .map((f) => `${PAPER_TO_CSS[f[0]]}:${f[1]}${unit}`)
        .join(";");
}

const RECORDSET_RE = /(?<resModel>(\w+.?)*)\((?<resIds>(\d*,?)*)\)/;
function recordSetReprToData(string) {
    const { resModel, resIds } = string.match(RECORDSET_RE).groups;
    return {
        resModel,
        resIds: resIds.split(",").flatMap((id) => (id ? parseInt(id) : [])),
    };
}

export function humanReadableError(error) {
    if (error.code === 200 && error.data) {
        error = error.data;
    }
    let viewError;
    if (error.context?.view) {
        // see @ def _raise_view_error.
        const { resIds, resModel } = recordSetReprToData(error.context.view);
        const { resIds: parentIds } = recordSetReprToData(error.context["view.parent"]);
        const viewName = error.context.name;
        viewError = {
            viewModel: resModel,
            completeName: error.context.xml_id ? `${viewName} (${error.context.xml_id})` : viewName,
            resIds,
            resModel: error.context["view.model"],
            parentIds,
        };
    }
    return {
        ...error,
        traceback: error.debug,
        viewError,
    };
}
