import { AutoComplete } from "@web/core/autocomplete/autocomplete";


export class PartnerAutoComplete extends AutoComplete {
    static template = "partner_autocomplete.PartnerAutoComplete";

    setup() {
        super.setup();
        this.shouldSearchWorldwide = false;
		this.shouldIncludeBranches = false;
	}

	// Override of AutoComplete
    loadOptions(options, request) {
        if (typeof options === "function") {
            return options(request, this.shouldSearchWorldwide, this.shouldIncludeBranches);
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

    async searchIncludeBranches(ev) {
		this.shouldIncludeBranches = true;
		ev.preventDefault();
		super.close();
		super.open(true);
    }
}
