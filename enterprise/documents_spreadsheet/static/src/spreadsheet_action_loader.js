import { addSpreadsheetActionLazyLoader } from "@spreadsheet/assets_backend/spreadsheet_action_loader";
import { _t } from "@web/core/l10n/translation";

addSpreadsheetActionLazyLoader("action_open_spreadsheet", "spreadsheet", _t("Spreadsheet"));
addSpreadsheetActionLazyLoader("action_open_template");
