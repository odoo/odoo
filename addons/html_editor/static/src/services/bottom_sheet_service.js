import { extra } from "@web/core/bottom_sheet/bottom_sheet_service";

const old = {
    ...extra,
};

extra.getBottomSheetOptions = (props, options) => ({
    ...old.getBottomSheetOptions(props, options),
    fitOnResize: options.fitOnResize,
});
