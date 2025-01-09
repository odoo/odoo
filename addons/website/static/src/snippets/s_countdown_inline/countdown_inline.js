
import { Countdown } from "@website/snippets/s_countdown/countdown";
import { registry } from "@web/core/registry";

export class CountdownInline extends Countdown {
    static selector = ".s_countdown_inline";

    setup() {
        this.countItemEls = this.el.querySelectorAll('.o_count_item');
        this.countItemNbsEls = this.el.querySelectorAll('.o_count_item_nbs');
        this.countItemNbEls = this.el.querySelectorAll('.o_count_item_nb');
        this.countItemlabelEls = this.el.querySelectorAll('.o_count_item_label');
        super.setup();
    }

    destroy() {
        this.el.querySelector(".s_countdown_inline_end_redirect_message")?.remove();
        this.el.querySelector(".s_countdown_inline_end_message")?.classList.add('d-none');
        clearInterval(this.setInterval);
    }

    /**
    * Isolates the first label letter to style correctly the "Compact" label style
    */
    wrapFirstLetter(string) {
        const firstLetter = string[0];
        const restOfString = string.slice(1);
        return `<span class="o_first_letter">${firstLetter}</span><span class="o_other_letters">${restOfString}</span>`;
    }

    initTimeDiff() {
        super.initTimeDiff();

        this.timeDiff.forEach(metric => {
            if (metric.label) {
                metric.label = this.wrapFirstLetter(metric.label);
            }
        });
    }

    render() {
        this.countItemEls = this.el.querySelectorAll('.o_count_item');
        this.countItemNbsEls = this.el.querySelectorAll('.o_count_item_nbs');
        this.countItemNbEls = this.el.querySelectorAll('.o_count_item_nb');
        this.countItemlabelEls = this.el.querySelectorAll('.o_count_item_label');
        super.render();

        // Clean each item
        for (const countItemEl of this.countItemEls) {
            countItemEl.classList.add('d-none');
        };
        for (const [i, metric] of this.timeDiff.entries()) {
            // Force to always have 2 numbers by metric
            metric.nb = String(metric.nb).padStart(2, '0');
            // If the selected template have inner element, wrap each number in each of them
            if (this.countItemNbEls.length > 0) {
                metric.nb.split("").forEach((number, index) => {
                    this.countItemNbsEls[i].querySelectorAll('span')[index].innerHTML = number;
                });
            } else {
                this.countItemNbsEls[i].innerHTML = String(metric.nb).padStart(2, '0');
            }
            this.countItemlabelEls[i].innerHTML = metric.label;
            this.countItemEls[i].classList.remove('d-none');
        };
        this.el.querySelector(".s_countdown_inline_wrapper").classList.toggle("d-none", this.shouldHideCountdown);
    }
};

registry
    .category("public.interactions")
    .add("website.countdownInline", CountdownInline);
