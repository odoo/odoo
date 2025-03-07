import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export function getDeleteOrArchiveDialogProps(deleteConfirmationDialogProps = null) {
    const orm = useService("orm");
    return async (resModel, resIds) => {
        const res = await orm.call(resModel, "get_restrict_constraints", [resIds]);
        if (res.models_with_blocking_records) {
            return {
                title: _t(`Delete ${res.model}`),
                body:`You cannot delete ${res.model.toLowerCase()}s containing ${res.models_with_blocking_records}. ` +
                    `${res.records_active ? "You can either archive them or first delete all their" : "You should first delete all of their"} ` +
                    `${res.models_with_blocking_records}.`
                ,
                confirm: res.records_active ? async() => {
                    await orm.call(
                        resModel,
                        "action_archive",
                        [resIds]
                    );
                    await this.model.load();
                } : null,
                confirmLabel: _t(`Archive ${res.model}s`),
                cancel: () => {},
                cancelLabel: _t("No, keep it"),
            };
        }
        return deleteConfirmationDialogProps;
    };
}
