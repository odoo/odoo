import { _t } from "@web/core/l10n/translation";

export class TestTranslationExportModel {
    testFunction() {
        function dummyFunction(term) {
            return term;
        }

        const dummy = {
            dummyFunction,
        };

        const term = "term";

        _t("JS Export 01 %s", "NO - JS Export 01");
        _t("JS Export 02 %(named)s", { named: "NO - JS Export 02" });

        _t("JS Export 03 %s", _t("JS Export 04 (Nested)"));
        _t("JS Export 05 %(named)s", { named: _t("JS Export 06 (Nested Named)") });

        _t("JS Export 07 %s", dummyFunction(_t("JS Export 08 (Double Nested)")));
        _t("JS Export 09 %(named)s", {
            named: dummyFunction(_t("JS Export 10 (Double Nested Named)")),
        });

        _t("JS Export 11 %s", dummy.dummyFunction(_t("JS Export 12 (Double Nested)")));
        _t("JS Export 13 %(named)s", {
            named: dummy.dummyFunction(_t("JS Export 14 (Double Nested Named)")),
        });

        _t("JS Export 15 %s", dummy["dummyFunction"](_t("JS Export 16 (Double Nested)")));
        _t("JS Export 17 %(named)s", {
            named: dummy["dummyFunction"](_t("JS Export 18 (Double Nested Named)")),
        });

        dummyFunction(_t("JS Export 19 (Base Nested)"));
        dummy.dummyFunction(_t("JS Export 20 (Base Nested)"));
        dummy["dummyFunction"](_t("JS Export 21 (Base Nested)"));

        _t("JS Export 22 %s", "NO - JS Export 03" + _t("JS Export 23"));
        _t("JS Export 24 %s", _t("JS Export 25") + "NO - JS Export 04");

        _t(`JS Export 26`);

        _t(dummyFunction`NO - JS Export 05`);
        _t(dummyFunction`NO - JS Export 06 ${term}`);

        _t(dummyFunction("NO - JS Export 07"));

        dummyFunction(`NO - JS Export 08${_t("JS Export 27")}NO - JS Export 09`);
    }
}
