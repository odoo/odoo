import { patch } from "@web/core/utils/patch";
import { AdditionalIdentifiersButton } from "@web/views/fields/additional_identifiers/additional_identifiers";

patch(AdditionalIdentifiersButton.prototype, {
    get identifiersInDropdown() {
        const hasSaudiIdentifier = Object.keys(this.state.identifiers).some((identifier) =>
            identifier.startsWith("SA_")
        );
        if (!hasSaudiIdentifier) {
            return super.identifiersInDropdown;
        }
        return super.identifiersInDropdown.filter(
            ({ identifierType }) => !identifierType.startsWith("SA_")
        );
    },

    onAdd(identifierType) {
        if (identifierType === "SA_TIN") {
            this.state.identifiers[identifierType] = this.props.record.data.vat.slice(0, 10) || "";
            this.debouncedCommitChanges();
        } else {
            super.onAdd(identifierType);
        }
    },
});
