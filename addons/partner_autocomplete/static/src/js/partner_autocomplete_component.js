import { AutoComplete } from "@web/core/autocomplete/autocomplete";


export class PartnerAutoComplete extends AutoComplete {
    static template = "partner_autocomplete.PartnerAutoComplete";

    setup() {
        super.setup();
        this.shouldSearchWorldwide = false;
		this.shouldIncludeBranch = false;
	}

	// Override of AutoComplete
    loadOptions(options, request) {
        if (typeof options === "function") {
            return options(request, this.shouldSearchWorldwide, this.shouldIncludeBranch);
        } else {
            return options;
        }
    }

	async searchWorldwide(ev){
		this.shouldSearchWorldwide = true;
		ev.preventDefault();
		super.close();
		super.open(true);
	}

    async searchIncludeEstablishments(ev) {
		this.shouldIncludeBranch = true;
		ev.preventDefault();
		super.close();
		super.open(true);
    }
}
