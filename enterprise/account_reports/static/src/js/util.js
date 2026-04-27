const LINE_ID_HIERARCHY_DELIMITER = "|";
const LINE_ID_GROUP_DELIMITER = "~";

export function buildLineId(current) {
    const convertNull = (value) => {
        if (value === null || value === undefined || value === false) {
            return "";
        } else if (typeof value === "object") {
            // We're using the replaceAll to follow the python
            // behavior where we're stringify a dict.
            return JSON.stringify(value).replaceAll('":', '": ');
        }
        return value;
    };

    return current
        .map(([markup, model, value]) => {
            const lineValues = [convertNull(markup), convertNull(model), convertNull(value)];
            return lineValues.join(LINE_ID_GROUP_DELIMITER);
        })
        .join(LINE_ID_HIERARCHY_DELIMITER);
}

export function parseLineId(lineID, markupAsString = false) {
    const parseMarkup = (markup) => {
        if (!markup) {
            return markup;
        }
        try {
            const result = JSON.parse(markup);
            return typeof result === "object" ? result : markup;
        } catch {
            return markup;
        }
    };

    if (!lineID) {
        return [];
    }
    return lineID.split(LINE_ID_HIERARCHY_DELIMITER).map((key) => {
        const [markup, model, value] = key.split(LINE_ID_GROUP_DELIMITER);
        return [
            (markupAsString ? markup : parseMarkup(markup)) || null,
            model || null,
            model && value ? parseInt(value) : value || null,
        ];
    });
}

export function removeTaxGroupingFromLineId(lineId) {
    // Tax grouping is not relevant for annotations, so we remove it from the line id.
    return buildLineId(
        parseLineId(lineId, true).filter(([markup, model, value]) => {
            return model !== "account.group";
        })
    );
}
