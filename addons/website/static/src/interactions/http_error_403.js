import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class HttpError403 extends Interaction {
    static selector = ".s_403_error";

    setup() {
        super.setup();
    }

    start() {
        this.handleDebugBlock();
        this.appendDemoErrorCard();
    }

    handleDebugBlock() {
        const debugBlock = this.el.querySelector(".debug_block");
        if (debugBlock) {
            debugBlock.classList.add("d-none");
            const errorBlock = this.el.querySelector(".error_block");
            if (errorBlock) {
                errorBlock.classList.remove("d-none");
            }
        }
    }

    appendDemoErrorCard() {
        const errorBlock = this.el.querySelector(".error_block");
        if (errorBlock && !this.el.querySelector(".card")) {
            const demoErrorCard = document.createElement("div");
            demoErrorCard.innerHTML = `
            <div class="container mb32 mt32">
                <div class="card">
                    <h4 class="card-header">
                        This is a demo error card.
                    </h4>
                    <div class="card-body">
                        This is a demo error card content. Any changes done into demo error card will not affect the actual error Content.
                        <br>
                        Changes outside this card will affect the actual error content.
                    </div>
                </div>
            </div>`;
            errorBlock.appendChild(demoErrorCard);
        }
    }
}

registry.category("public.interactions.edit").add("website.http_error_403", {
    Interaction: HttpError403,
});
