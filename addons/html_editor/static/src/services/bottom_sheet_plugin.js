import { extra } from "@web/core/bottom_sheet/bottom_sheet_plugin";

const old = {
    ...extra,
};

extra.getBottomSheetOptions = (props, options) => ({
    ...old.getBottomSheetOptions(props, options),
    withUnfocus: options.withUnfocus,
});
