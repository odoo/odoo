
import { Countdown } from "@website/snippets/s_countdown/countdown";
import { registry } from "@web/core/registry";

export class CountdownInline extends Countdown {
    static selector = ".s_countdown_inline";

    setup() {
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
        super.render();

        const countItemEls = this.el.querySelectorAll('.o_count_item');
        const countItemNbsEls = this.el.querySelectorAll('.o_count_item_nbs');
        const countItemNbEls = this.el.querySelectorAll('.o_count_item_nb');
        const countItemlabelEls = this.el.querySelectorAll('.o_count_item_label');
        // Clean each item
        countItemEls.forEach((item, i) => {
            countItemEls[i].classList.add('d-none');
        });
        this.timeDiff.forEach((item, i) => {
            // Force to always have 2 numbers by metric
            item.nb = String(item.nb).padStart(2, '0');
            // If the selected template have inner element, wrap each number in each of them
            if (countItemNbEls.length > 0) {
                item.nb.split("").forEach((number, index) => {
                    countItemNbsEls[i].querySelectorAll('span')[index].innerHTML = number;
                });
            } else {
                countItemNbsEls[i].innerHTML = String(item.nb).padStart(2, '0');
            }
            countItemlabelEls[i].innerHTML = item.label;
            countItemEls[i].classList.remove('d-none');
        });
        this.el.querySelector(".s_countdown_inline_wrapper").classList.toggle("d-none", this.shouldHideCountdown);
    }
};

registry
    .category("public.interactions")
    .add("website.countdownInline", CountdownInline);

registry
    .category("public.interactions.edit")
    .add("website.countdownInline", {
        Interaction: CountdownInline,
    });
