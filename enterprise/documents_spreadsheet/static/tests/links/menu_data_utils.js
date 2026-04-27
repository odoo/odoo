import { getMenuServerData as getSpreadsheetMenuServerData } from "@spreadsheet/../tests/links/menu_data_utils";
import { getDocumentBasicData } from "@documents_spreadsheet/../tests/helpers/data";

export const getMenuServerData = () => {
    const res = getSpreadsheetMenuServerData();
    res.models["res.users"] = getDocumentBasicData().models["res.users"];
    return res;
};
